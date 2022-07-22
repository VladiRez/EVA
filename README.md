# Einführung

Dies ist der Digitale Zwilling eines Automata EVA Roboters.

# DIGITAL TWIN INSTALLATION

1. Virtuelle Umgebung initialisieren
> py -m venv eva_env

2. In Venv einklinken: activate ausführen
> .\eva_env\Scripts\activate

3. pip install -r requirements.txt

# DPT Base Module benutzen

Schritt 3 der Installation sollte das DPT Base Module mit Pip im Development Mode installiert sein.
Ein DPT Modul erstellt man dann, indem man von DptModule erbt.
Es darf nicht vergessen werden, den DptModule Konstruktor aufzurufen, wenn man eine eigene Konstruktormethode implementiert (super().__init__()). 

# DPT Starten

Momentan müssen die DPT Module noch separat gestartet werden.

1. MongoDB Starten: \DPT\DATA\op_data\start_db.bat
2. Broker starten (\DPT\CONTROL\broker.py  Broker().mediate())
3. Interface (\DPT\INTERFACE\eva.py  EvaInterface()), Operational Database (\DPT\DATA\op_data\op_data.py  OpData()) starten.
4. Django Dev-Server starten
> python \DPT\UI\process_ui\manage.py runserver
5. GUI ist erreichbar auf 127.0.0.1/toolpaths

Schritt 2, 3 und 4 übernimmt momentan die django_test.py (\DPT\testing\django_test.py).

