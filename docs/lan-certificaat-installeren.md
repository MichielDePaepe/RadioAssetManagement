# LAN-certificaat installeren op clients

Voor camera-scannen en Web Serial moet de browser de site als betrouwbaar HTTPS
zien. Installeer daarom het CA-certificaat `ram-lan-ca.crt` op elk toestel dat
de applicatie gebruikt.

Gebruik **niet** `ram-lan.key` of `ram-lan-ca.key` op clients. Dat zijn private
keys en blijven op de server.

## Bestand kopieren

Kopieer dit bestand van de server naar het clienttoestel:

```text
certs/ram-lan-ca.crt
```

Dat kan via USB-stick, AirDrop, mail, gedeelde map of een interne downloadlink.

## Windows

1. Dubbelklik op `ram-lan-ca.crt`.
2. Klik op **Certificaat installeren**.
3. Kies **Lokale computer**.
4. Kies **Alle certificaten in het onderstaande archief opslaan**.
5. Klik op **Bladeren**.
6. Kies **Vertrouwde basiscertificeringsinstanties**.
7. Klik op **Volgende** en daarna **Voltooien**.
8. Sluit Chrome of Edge volledig en open de browser opnieuw.

Controleer daarna:

```text
https://<host-of-ip>:<poort>
```

## macOS

1. Open `ram-lan-ca.crt`.
2. Sleutelhangertoegang opent automatisch.
3. Zet het certificaat in de sleutelhanger **Systeem**.
4. Open het certificaat in Sleutelhangertoegang.
5. Klap **Vertrouw** open.
6. Zet **Bij gebruik van dit certificaat** op **Vertrouw altijd**.
7. Sluit het venster en bevestig met het beheerderswachtwoord.
8. Sluit Chrome, Edge of Safari volledig en open de browser opnieuw.

## iPhone en iPad

1. Open `ram-lan-ca.crt` op het toestel.
2. iOS meldt dat er een profiel is gedownload.
3. Ga naar **Instellingen**.
4. Tik bovenaan op **Profiel gedownload**.
5. Tik op **Installeer**.
6. Voer de toegangscode in.
7. Bevestig opnieuw met **Installeer**.
8. Ga naar **Instellingen** > **Algemeen** > **Info**.
9. Scroll naar beneden en open **Vertrouwensinstellingen certificaten**.
10. Zet **Radio Asset Management LAN CA** aan.
11. Bevestig met **Ga door**.
12. Sluit Safari of Chrome volledig en open de browser opnieuw.

Let op: camera-scannen werkt op iPhone via HTTPS. Web Serial werkt niet op iOS;
seriele communicatie blijft desktop Chrome of Edge.

## Android

De exacte namen verschillen per merk en Android-versie.

1. Zet `ram-lan-ca.crt` op het toestel.
2. Ga naar **Instellingen**.
3. Zoek naar **Certificaat installeren** of ga naar **Beveiliging**.
4. Kies **CA-certificaat**.
5. Selecteer `ram-lan-ca.crt`.
6. Bevestig de waarschuwing.
7. Geef het certificaat een herkenbare naam, bijvoorbeeld `RAM LAN CA`.
8. Sluit Chrome volledig en open opnieuw.

Bij sommige Android-toestellen vertrouwt Chrome zelf-geinstalleerde CA's niet
voor alle bedrijfsprofielen. Test daarom altijd de echte URL na installatie.

## Controle

Open de applicatie in de browser. Er mag geen privacy- of certificaatwaarschuwing
meer verschijnen.

Voorbeeld:

```text
https://172.20.18.70:8443
```

Als Chrome of Safari nog `ERR_CERT_AUTHORITY_INVALID` of een privacywaarschuwing
toont, is het CA-certificaat nog niet volledig vertrouwd op dat toestel.
