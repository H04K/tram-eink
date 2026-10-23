// tram-eink : programme du reTerminal E1001 (ESP32-S3, e-ink 7,5" 800x480 noir et blanc)
//
// Se réveille, télécharge status.json puis dashboard.bin, affiche l'image si elle a changé,
// et se rendort le nombre de secondes indiqué par "refresh_s".
// Bouton vert (à droite) : rafraîchir tout de suite.
//
// Arduino IDE : carte "XIAO_ESP32S3", PSRAM "OPI PSRAM", bibliothèque GxEPD2.
// Broches d'après le wiki Seeed (reterminal_e10xx_with_arduino).

#include <GxEPD2_BW.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <esp_sleep.h>

#include "secrets.h"

#define EPD_SCK 7
#define EPD_MOSI 9
#define EPD_CS 10
#define EPD_DC 11
#define EPD_RST 12
#define EPD_BUSY 13
#define KEY_REFRESH GPIO_NUM_3  // bouton vert, actif à l'état bas
#define LED_PIN 6               // logique inversée : LOW = allumée

const int W = 800, H = 480, IMG_BYTES = W * H / 8;
const int FULL_REFRESH_EVERY = 20;  // un rafraîchissement complet de temps en temps efface les fantômes

GxEPD2_BW<GxEPD2_750_GDEY075T7, GxEPD2_750_GDEY075T7::HEIGHT> display(
    GxEPD2_750_GDEY075T7(EPD_CS, EPD_DC, EPD_RST, EPD_BUSY));
SPIClass hspi(HSPI);

// conservé pendant le sommeil profond
RTC_DATA_ATTR uint32_t lastCrc = 0;
RTC_DATA_ATTR uint32_t updates = 0;
RTC_DATA_ATTR bool panelAwake = false;  // contrôleur resté alimenté : partiel possible

uint32_t crc32(const uint8_t *data, size_t len) {
  uint32_t crc = 0xFFFFFFFF;
  for (size_t i = 0; i < len; i++) {
    crc ^= data[i];
    for (int k = 0; k < 8; k++) crc = (crc >> 1) ^ (0xEDB88320 & -(crc & 1));
  }
  return ~crc;
}

void sleepFor(uint32_t seconds) {
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
  esp_sleep_enable_timer_wakeup((uint64_t)seconds * 1000000ULL);
  esp_sleep_enable_ext0_wakeup(KEY_REFRESH, 0);
  esp_deep_sleep_start();
}

bool wifiConnect() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  for (int i = 0; i < 60 && WiFi.status() != WL_CONNECTED; i++) delay(250);
  return WiFi.status() == WL_CONNECTED;
}

// GET vers BASE_URL + path ; remplit buf (jusqu'à cap octets), renvoie la taille lue ou -1
int fetch(const char *path, uint8_t *buf, int cap) {
  String url = String(BASE_URL) + path;
  WiFiClientSecure tls;
  WiFiClient plain;
  HTTPClient http;
  if (url.startsWith("https")) {
    tls.setInsecure();  // image publique : on ne vérifie pas le certificat
    http.begin(tls, url);
  } else {
    http.begin(plain, url);
  }
  http.setTimeout(20000);
  if (http.GET() != HTTP_CODE_OK) {
    http.end();
    return -1;
  }
  WiFiClient *stream = http.getStreamPtr();
  int n = 0;
  unsigned long start = millis();
  while (n < cap && http.connected() && millis() - start < 20000) {
    int got = stream->readBytes(buf + n, cap - n);
    if (got <= 0) break;
    n += got;
  }
  http.end();
  return n;
}

void setup() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);
  bool button = esp_sleep_get_wakeup_cause() == ESP_SLEEP_WAKEUP_EXT0;
  if (button) digitalWrite(LED_PIN, LOW);  // petit retour visuel

  if (!wifiConnect()) sleepFor(120);

  char status[1024] = {0};
  uint32_t refresh = 300;
  if (fetch("/status.json", (uint8_t *)status, sizeof(status) - 1) > 0) {
    char *p = strstr(status, "\"refresh_s\":");
    if (p) refresh = constrain(atoi(p + 12), 30, 3600);
  }

  uint8_t *img = (uint8_t *)ps_malloc(IMG_BYTES);
  if (!img || fetch("/dashboard.bin", img, IMG_BYTES) != IMG_BYTES) sleepFor(120);

  uint32_t crc = crc32(img, IMG_BYTES);
  if (crc != lastCrc || button) {
    hspi.begin(EPD_SCK, -1, EPD_MOSI, -1);
    display.epd2.selectSPI(hspi, SPISettings(2000000, MSBFIRST, SPI_MODE0));
    // partiel (sans clignoter) seulement si le contrôleur a gardé l'image précédente
    bool full = !panelAwake || button || updates % FULL_REFRESH_EVERY == 0;
    display.init(0, full, 2, false);
    display.setFullWindow();
    display.fillScreen(GxEPD_WHITE);
    display.drawBitmap(0, 0, img, W, H, GxEPD_BLACK);  // dans le .bin, 1 = noir
    display.display(!full);
    // prochain réveil proche : on coupe juste la haute tension (le contrôleur garde l'image) ;
    // sinon sommeil profond de l'écran, et le prochain affichage sera complet
    panelAwake = refresh <= 300;
    if (panelAwake) display.powerOff();
    else display.hibernate();
    lastCrc = crc;
    updates++;
  }
  digitalWrite(LED_PIN, HIGH);
  sleepFor(refresh);
}

void loop() {}
