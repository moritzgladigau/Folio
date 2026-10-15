<h1 align="center">Folio</h1>

<p align="center">
  <img src="assets/folio-readonly-256.png" alt="Folio-Icon: Dokument mit Lupe" width="160">
</p>

<p align="center"><strong>ReadOnly Dokumentenbrowser</strong></p>

Folio zeigt Markdown, Text, RTF, PDF, HTML, DOCX, ODT und gängige Bilder aus **einem** ausgewählten Verzeichnis an. Die Oberfläche bietet Baumansicht, Pfadsuche, Verlauf, Dokumentwechsel und Zoom. Die Anwendung benötigt kein Netzwerk.

> **Projektstatus:** Folio ist eine pragmatische Schnelllösung. Die Implementierung wurde weit überwiegend, möglicherweise nahezu vollständig, mit OpenAI Codex erstellt. Anforderungen und Entscheidungen wurden im Dialog mit Codex festgelegt. Das Projekt wurde nicht unabhängig sicherheitsgeprüft.

Unterstützte Textdateien: `.txt`, `.text`, `.log`, `.csv`, `.tsv`, `.json`, `.jsonl`, `.xml`, `.yaml`, `.yml`, `.ini`, `.cfg`, `.conf`, `.toml`, `.rst`, `.tex`, `.sql`, `.py`, `.sh`, `.css` und `.js`. Bilder: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.bmp`, `.tif`, `.tiff`, `.ico`, `.pbm`, `.pgm`, `.ppm` und `.svg`. Animierte GIFs zeigen das erste Bild. RTF wird als Text dargestellt. DOCX/ODT erhalten eine Vorschau für Text, Überschriften, Listen und einfache Tabellen; komplexes Layout, eingebettete Medien und Makros werden nicht ausgeführt oder dargestellt. Alte binäre `.doc`-Dateien werden nicht unterstützt.

## Installation auf Ubuntu

Benötigt werden Python 3, `python3-venv`, Bubblewrap und die von Qt verwendeten Systembibliotheken. `install.sh` installiert fehlende Ubuntu-Pakete bei Bedarf und verlangt dafür `sudo`.

```bash
git clone git@github.com:moritzgladigau/Folio.git
cd Folio
./install.sh --desktop "$HOME/Dokumente/MeineSammlung"
```

Der Dokumentenordner ist optional. Ohne ihn installiert das Skript die Anwendung, startet sie aber noch nicht. Mit `--desktop` richtet es den Starter und das Folio-Icon im Anwendungsmenü ein. Es prüft Bubblewrap, richtet nur bei dem bekannten Ubuntu-Berechtigungsfehler das AppArmor-Profil ein, installiert die Python-Pakete in `.venv`, führt die Tests aus und startet bei angegebenem Ordner die Anwendung. Das Skript selbst **ohne `sudo`** ausführen; es fordert Administratorrechte nur für fehlende Systempakete oder das AppArmor-Profil an.

## Deinstallation

```bash
cd Folio
./uninstall.sh
```

Das Skript entfernt den zu diesem Projekt gehörenden Anwendungsstarter und die Icon-Dateien, den Befehl `folio` (gegebenenfalls auch die ältere Verknüpfung `docbrowser`), die lokale `.venv` und das Startprotokoll. Es benötigt kein `sudo`. Der Projektordner und die ausgewählten Dokumente bleiben erhalten und können danach bei Bedarf manuell gelöscht werden. Ubuntu-Pakete und das systemweite Bubblewrap-AppArmor-Profil bleiben installiert, da sie auch von anderen Anwendungen verwendet werden können.

Falls nach der Ordnerauswahl kein Fenster erscheint, starte denselben Ordner aus einem Terminal mit `./run.sh "/pfad/zum/ordner"`. Der Starter zeigt Startfehler zusätzlich als Dialog an und speichert das Protokoll unter `~/.local/state/docbrowser/last-launch.log`. Nach einer Aktualisierung des Projekts `./install.sh --desktop` erneut ausführen.

### Ubuntu/AppArmor: `loopback: Failed RTM_NEWADDR`

Wenn das Startprotokoll `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted` enthält, verweigert Ubuntu Bubblewrap die nötigen Rechte zum Aufbau der Sandbox. Das ist kein Fehler der Python-Abhängigkeiten oder des Dokumentenordners. Ubuntu 24.04 und neuer beschränken unprivilegierte User-Namespaces über AppArmor. [Ubuntu beschreibt diese Einschränkung und gezielte AppArmor-Profile in den 24.04-Versionshinweisen](https://documentation.ubuntu.com/release-notes/24.04/#unprivileged-user-namespace-restrictions).

Prüfe zunächst, ob das von Ubuntu bereitgestellte Bubblewrap-Profil vorhanden ist:

```bash
ls -l /etc/apparmor.d/bwrap-userns-restrict /usr/share/apparmor/extra-profiles/bwrap-userns-restrict
```

`install.sh` führt die folgenden Befehle selbst aus, falls die Sandbox genau an dieser Berechtigung scheitert und das Profil noch nicht installiert ist:

```bash
sudo install -m 0644 /usr/share/apparmor/extra-profiles/bwrap-userns-restrict /etc/apparmor.d/bwrap-userns-restrict
sudo apparmor_parser -r /etc/apparmor.d/bwrap-userns-restrict
```

Fehlt die Quelldatei, installiert es zuvor `apparmor-profiles`. Nach dem Laden testet es Bubblewrap erneut und bricht bei einem verbleibenden Fehler ab. Das Profil gilt systemweit für Bubblewrap; die globale AppArmor-Beschränkung wird nicht abgeschaltet.

### Qt WebEngine: OpenGL-Fehler

In der Sandbox werden keine GPU-Geräte eingebunden. `run.sh` setzt deshalb `QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu` und `QT_QUICK_BACKEND=software`. Das entspricht den [Qt-Hinweisen zum Software-Rendering](https://doc.qt.io/qt-6/qtwebengine-features.html#force-use-of-software-rendering) und benötigt keine Änderung an der Dateisystem- oder Netzwerkisolierung.

## Start und Bedienung

```bash
./run.sh /home/user/Dokumente/Wissenssammlung
```

Ohne Argument erscheint vor dem Sandbox-Start ein Ordnerdialog. Im Anwendungsmenü heißt der Starter **Folio**; Ordner können als Argument übergeben werden. Nach der Installation funktioniert auch der Terminalbefehl `folio [Dokumentenordner]`. `run.sh` verweigert den Start, wenn Bubblewrap fehlt oder das Verzeichnis ungültig ist. **Für die Sicherheitsgarantien immer `run.sh` beziehungsweise den installierten Starter verwenden.** `main.py` allein startet nur die innere Anwendung ohne Betriebssystem-Sandbox.

Links können Ordner auf- und zugeklappt und Dokumente nach Dateiname, Endung oder relativem Pfad gefiltert werden. Die Werkzeugleiste bietet Verlauf, voriges/nächstes Dokument und Zoom. PDF-Seiten lassen sich zusätzlich im PDF-Bereich wechseln. Text wird mit Zeilenumbruch angezeigt; Monospace ist umschaltbar.

## Sicherheitsmodell

`SecureFileAccess` ist der einzige Leseweg für Dokumente und eingebettete Bilder. Es akzeptiert nur relative Pfade ohne `.` oder `..`, öffnet jede Verzeichniskomponente relativ zu einem bereits geöffneten Verzeichnisdeskriptor und verwendet `O_NOFOLLOW`. So werden Symlinks und ein Austausch zwischen Pfadprüfung und Öffnung abgewehrt. Es stellt keinerlei Schreib-, Umbenennungs- oder Löschmethode bereit. Abgewiesene Zugriffe werden protokolliert. Dokumente bis 128 MiB, Text bis 16 MiB, Bilder bis 16 MiB und Office-Archive bis 64 MiB werden verarbeitet. Aus DOCX/ODT wird nur die XML-Hauptdatei bis 16 MiB gelesen; externe Beziehungen und Dateien werden nicht geladen.

Markdown und HTML werden in einem eigenen `doc://root/`-Schema geladen. Der Scheme-Handler liest Ressourcen ausschließlich über `SecureFileAccess`. WebEngine blockiert fremde Schemas und Hosts; JavaScript, Plugins, lokale `file://`-Zugriffe, Downloads und neue Fenster sind deaktiviert. Eine Content-Security-Policy sperrt Skripte, Netzwerkverbindungen, Frames, Formulare und externe Inhalte zusätzlich. Links innerhalb der Sammlung können geöffnet werden. Qt PDF lädt aus einem Speicherpuffer; die Originaldatei wird nicht an den PDF-Viewer weitergereicht.

**Die Prozessgrenze kommt von Bubblewrap.** `run.sh` bindet nur die Anwendung, Systembibliotheken und die Dokumentensammlung ein; letztere ausschließlich read-only unter `/documents`. Es erstellt ein temporäres Home, einen temporären `/tmp`-Bereich und einen eigenen Netzwerk-Namespace. Für die Anzeige wird nur der verwendete Wayland- oder X11-Socket eingebunden. Andere Benutzerverzeichnisse werden nicht eingebunden. Damit kann der gestartete Prozess weder Originaldokumente schreiben noch über gewöhnliche Dateipfade andere Benutzerdateien lesen. Die innere Pfadprüfung allein wäre keine Betriebssystem-Sandbox. Ein X11-Server kann prinzipbedingt weitergehende Desktop-Zugriffe zulassen; für die stärkere Desktop-Isolation Wayland verwenden. Ein Benutzer mit Kontrolle über den App-Code oder den Startbefehl kann die Sandbox umgehen; diese Lösung schützt gegen fehlerhafte und bösartige Dokumentinhalte, nicht gegen einen bereits kompromittierten Benutzeraccount.

Die Ordnerauswahl läuft notwendigerweise vor der Sandbox. Dabei wird nur ein Pfad gewählt und an den isolierten Prozess übergeben. Die Sammlung sollte während des Starts nicht von einem anderen Prozess ausgetauscht werden. Ein auf dem Host befindliches Bind-Mount im ausgewählten Ordner ist kein Symlink und kann weitere Inhalte enthalten; solche Mounts müssen vor der Auswahl geprüft werden.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Die Tests decken erlaubte Lesezugriffe, Pfad-Traversal, Symlinks, Austausch vor dem Öffnen, Read-Only-API, unveränderte Originaldateien, Navigation und Ressourcenrichtlinien ab. Für die tatsächliche Desktop-Ausführung und die Bubblewrap-Konfiguration ist ein Ubuntu-System mit grafischer Sitzung erforderlich.

## Lizenz

Der Folio-Quellcode und das App-Icon stehen unter der [MIT-Lizenz](LICENSE). Die verwendeten Python- und Qt-Abhängigkeiten behalten ihre jeweiligen eigenen Lizenzen.
