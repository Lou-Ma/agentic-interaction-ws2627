# Delegationsgrenze

Übung 2 · Agentic Interaction · WS 2026/27 · Universität Ulm

## Klassifikation

| #   | Aktion                                       | Entscheidung | Begründung                                                                                                                                                                                                                |
| --- | -------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Termine eines Tages lesen                    | alone        | Da der reine Lesezugriff nichts ändert und es niemanden sonst betrifft, soll der Agent dies alleine machen. Außerdem wäre es lästig wenn der Agent bei jeder Frage wie „Was steht heute an?“ um Erlaubnis bitte.
| 2   | Wetter abfragen                              | alone        | Die Abfrage ist ein reiner Lesezugriff auf öffentliche Daten und hat keine Folgen. Eine Rückfrage würde mich nur Zeit kosten, daher soll der Agent dies alleine machen.                                                                                                                              |
| 3   | Zugverbindungen suchen                       | alone        | Dies ist ein reiner Lesezugriff und eine einfache Suche verpflichtet zu nichts. Da der Agent diese Informationen braucht, um überhaupt einen guten Vorschlag machen zu können, kann er dies alleine machen.                                                                        |
| 4   | Notizen lesen                                | alone        | Meine Notizen sind zwar persönlich, aber der Agent handelt in meinem Auftrag und liest sie nur für mich. Da nichts das System verlässt und nichts wird verändert wird, kann der Agent das alleine machen.                                                                          |
| 5   | Persönlichen Block im Kalender anlegen       | alone        | Es betrifft nur meinen eigenen Kalender und niemand anderes wird benachrichtigt. Außerdem lässt sich der Eintrag leicht wieder entfernen und Reisezeit zu blocken ist genau die Art Routinearbeit, die ich abgeben möchte.                      |
| 6   | Termin mit anderen Teilnehmenden verschieben | approval     | Hier sind noch andere Personen betroffen und werden sofort benachrichtigt. Wenn ein Fehler auftritt kostet das sowhol ihre Zeit als auch etwas von meiner Glaubwürdigkeit und lässt sich nicht unbemerkt rückgängig machen.                                                      |
| 7   | Zugticket buchen                             | approval     | Dies kostet Geld und schafft eine Verpflichtung, die schwer oder nur mit weiteren Kosten rückgängig zu machen ist. Welcher Zug passt, hängt außerdem von Dingen ab, die der Agent evtl. nicht kennt (z. B. wie viel Puffer ich möchte). |
| 8   | Nachricht an Dritte senden                   | approval     | Da sich eine gesendete Nachricht nicht zurückholen lässt und in meinem Namen gesprochen wird, sollte der Wortlaut und Empfänger vor dem Versand von mir bestätigt werden.                                                                       |
| 9   | Notiz anlegen                                | alone        | Hierbei fügt der Agent nur etwas in meinem eigenen Bereich hinzu, es schadet niemandem und ist auch trivial rückgängig zu machen.                                                                                                                      |
| 10  | Notiz löschen                                | approval     | Dies ist ein unumkehrbarer Datenverlust und da „aufräumen“ mehrdeutig ist, könnte es für den Agenten wie Ballast aussehen, mir aber noch wichtig sein. Daher möcht ich dies vorher freigeben.                                                                                       |

## Meine Regel

Der Agent handelt allein, solange er nur liest oder leicht umkehrbare Änderungen in meinem eigenen Bereich vornimmt; sobald eine Aktion andere Personen betrifft, Geld kostet oder nicht rückgängig zu machen ist, fragt er vorher.

## Beobachtungen aus dem Rollenspiel

1. **Beobachtung 1:** Karte E: Der Agent hat die Nachricht an das Stand-up formuliert und gleich abgeschickt. Ich hätte den Wortlaut vorher sehen wollen, vor allem den Ton. Das bestätigt approval bei Nachrichten an Dritte.
2. **Beobachtung 2:** Karte B: Der Agent hat direkt ein Ticket gebucht, ohne zu sagen, was es kostet oder ob es Alternativen gab. Mir fehlten Preis und Abfahrtszeit für die Entscheidung. Das stützt mein approval bei Buchungen
