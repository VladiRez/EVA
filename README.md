# Einführung

Dies ist der Digitale Zwilling eines Automata EVA Roboters.

# DIGITAL TWIN INSTALLATION

1. Virtuelle Umgebung initialisieren
> py -m venv eva_env

2. In Venv einklinken: activate ausführen
> .\eva_env\Scripts\activate

3. pip install -r requirements.txt

# DPT Base Module benutzen

Durch Schritt 3 der Installation sollte das DPT Base Module mit Pip im Development Mode installiert sein.
Ein DPT Modul erstellt man dann, indem eine Klasse von DptModule erbt oder ein Skript ein DptModule Objekt instanziiert.
Beim erben darf nicht vergessen werden, den DptModule Konstruktor aufzurufen, wenn man eine eigene Konstruktormethode implementiert (super().__init__()). 

# DPT Starten

Momentan müssen die DPT Module noch separat gestartet werden.

1. MongoDB Starten: \DPT\DATA\op_data\start_db.bat
2. Broker starten (\DPT\CONTROL\broker.py  Broker().mediate())
3. Interface (\DPT\INTERFACE\eva.py  EvaInterface()), Operational Database (\DPT\DATA\op_data\op_data.py  OpData()) starten.
4. Django Dev-Server starten (User Interface)
> python \DPT\UI\process_ui\manage.py runserver
5. GUI ist erreichbar auf 127.0.0.1/toolpaths

Schritt 2, 3 und 4 übernimmt momentan die django_test.py (\DPT\testing\django_test.py).

# Kommunikation zwischen Modulen

Die Kommunikation im DPT läuft über zeromq mithilfe einer Brokers. Implementiert ist die Kommunikation im DptModule (Base Module), dort sind die Funktionen transmit und receive dokumentiert.
Im Base Module gibt es zwei Enumerators die Konstanten darstellen: Requests und Responses. Sie stehen für spezifische Nachrichten-Typen und können erweitert werden. Jedes Modul kennt diese Konstanten.

Eine ZeroMQ Nachricht hat in diesem DPT folgende Struktur: Sie ist ein python-tuple, wobei der erste Eintrag ein Request oder Response Enum ist (Nachrichtentyp/Befehl). Alternativ kann auch statt einem Tuple nur der Nachrichtentyp verschickt werden, wenn sonst keine Daten übertragen werden müssen. Des weiteren kann der Inhalt des Tuples frei gewählt werden. 

Ist die Bearbeitung eines Befehls erfolgreich, wird der Befehl selbst zurückgeschickt. Beispiel: UI an Datenbank: NEW_WP, Datenbank erstellt neuen Waypoint, Datenbank an UI: New_WP, fertig.

# GITHUB RICHTLINIEN

BITTE NUR QUELLCODE IM GITHUB HOCHLADEN! Binärdateien haben im Regelfall nichts im Repository verloren. Oft, wie im fall von Venvs oder Datenbanken, funktioniert deren Synchronisation auch gar nicht über git.
