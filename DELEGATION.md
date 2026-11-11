# Delegationsgrenze

Übung 2 · Agentic Interaction · WS 2026/27 · Universität Ulm

## Klassifikation

| #   | Aktion                                       | Entscheidung | Begründung                                                                                                                                                                                                                |
| --- | -------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Termine eines Tages lesen                    | alone        | Reiner Lesezugriff, ändert nichts und betrifft niemanden sonst. Bei jeder Frage wie „Was steht heute an?“ um Erlaubnis zu bitten, wäre lästig und brächte keine zusätzliche Sicherheit.                                   |
| 2   | Wetter abfragen                              | alone        | Reiner Lesezugriff auf öffentliche Daten, ohne Folgen. Eine Rückfrage würde nur Zeit kosten.                                                                                                                              |
| 3   | Zugverbindungen suchen                       | alone        | Reiner Lesezugriff; eine Suche verpflichtet zu nichts. Der Agent braucht diese Informationen, um überhaupt einen guten Vorschlag machen zu können.                                                                        |
| 4   | Notizen lesen                                | alone        | Notizen sind persönlich, aber der Agent handelt in meinem Auftrag und liest sie nur für mich; nichts verlässt das System, nichts wird verändert.                                                                          |
| 5   | Persönlichen Block im Kalender anlegen       | alone        | Betrifft nur meinen eigenen Kalender, niemand wird benachrichtigt, und der Eintrag lässt sich leicht wieder entfernen. Reisezeit zu blocken ist genau die Art Routinearbeit, die ich abgeben möchte.                      |
| 6   | Termin mit anderen Teilnehmenden verschieben | approval     | Andere Personen sind betroffen und werden sofort benachrichtigt; ein Fehler kostet ihre Zeit und meine Glaubwürdigkeit und lässt sich nicht still rückgängig machen.                                                      |
| 7   | Zugticket buchen                             | approval     | Kostet Geld und schafft eine Verpflichtung, die schwer oder nur mit Kosten rückgängig zu machen ist. Welcher Zug passt, hängt außerdem von Dingen ab, die der Agent evtl. nicht kennt (z. B. wie viel Puffer ich möchte). |
| 8   | Nachricht an Dritte senden                   | approval     | Eine gesendete Nachricht lässt sich nicht zurückholen und spricht in meinem Namen. Wortlaut und Empfänger sollten vor dem Versand bestätigt werden.                                                                       |
| 9   | Notiz anlegen                                | alone        | Fügt nur etwas in meinem eigenen Bereich hinzu, schadet nichts und ist trivial rückgängig zu machen.                                                                                                                      |
| 10  | Notiz löschen                                | approval     | Unumkehrbarer Datenverlust; „aufräumen“ ist mehrdeutig, und was für den Agenten wie Ballast aussieht, kann mir noch wichtig sein.                                                                                         |

## Meine Regel

Der Agent handelt allein, solange er nur liest oder leicht umkehrbare Änderungen in meinem eigenen Bereich vornimmt; sobald eine Aktion andere Personen betrifft, Geld kostet oder nicht rückgängig zu machen ist, fragt er vorher.

## Beobachtungen aus dem Rollenspiel

1. **Beobachtung 1:** Karte E: Der Agent hat die Nachricht an das Stand-up formuliert und gleich abgeschickt. Ich hätte den Wortlaut vorher sehen wollen, vor allem den Ton. Das bestätigt approval bei Nachrichten an Dritte.
2. **Beobachtung 2:** Karte B: Der Agent hat direkt ein Ticket gebucht, ohne zu sagen, was es kostet oder ob es Alternativen gab. Mir fehlten Preis und Abfahrtszeit für die Entscheidung. Das stützt mein approval bei Buchungen
