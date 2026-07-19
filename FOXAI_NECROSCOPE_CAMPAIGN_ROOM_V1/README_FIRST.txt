FOXAI NECROSCOPE CAMPAIGN ROOM V1

WHAT THIS IS

A standalone localhost Campaign Room designed to let Eric play a private,
source-grounded Necroscope campaign with Agent Fox next week without modifying
the main FOXAI WebUI.

FEATURES

- Uses FOXAI's active local model at 127.0.0.1:8080
- Searches the private Necroscope SQLite page index before every Agent Fox turn
- Supplies book title and PDF page references to the model
- Saves a private transcript and machine-readable session log
- Provides seven quick-start E-Branch roles
- Includes the MasterBook 2d10 Bonus Number chart
- Calculates Action Total, Result Points, and final Effect Value
- Offers Canon Only and Canon + Original Gaps modes
- Includes Agent-Managed, Visible, and Off deck modes
- Archives campaign state before a reset

IMPORTANT DECK NOTE

The owned Necroscope worldbook states that the MasterDeck is optional but
recommended. The exact deck procedure remains inside the image-only MasterBook
Corebook and was not recovered by the text index.

Campaign Room V1 therefore uses an ORIGINAL FOXAI STORY DECK as a temporary
proxy. It contains 36 newly written Edge, Complication, and Turning Point cards.
It is not a transcription, reproduction, or claim of exact MasterDeck behavior.

Agent-Managed mode quietly checks the proxy deck every third player turn.
Applied cards are always recorded in session_log.jsonl. The player can reveal
the deck state at any time.

MASTERBOOK ROLL

Campaign Room uses this recovered Bonus Number structure:

2=-10
3=-8
4=-7
5=-6
6=-5
7=-3
8-9=-1
10-11=0
12=+1
13=+2
14=+3
15=+4
16=+5
17=+6
18=+7
19=+8
20-24=+9
25-29=+10
30-34=+11
35-39=+12
40-44=+13
45-49=+14
Every additional full 5 points adds +1.

Action Total = Skill + Bonus Number
Result Points = Action Total - Difficulty Number

The recovered Necroscope examples add successful Result Points to Effect Value.

INSTALL

1. Extract this entire folder directly inside:
   Z:\FOXAI

2. Start FOXAI WebUI.

3. In Artificial Minds, start Fast Talk or Creative Brain.

4. Open:
   Z:\FOXAI\FOXAI_NECROSCOPE_CAMPAIGN_ROOM_V1

5. Run:
   RUN_NECROSCOPE_CAMPAIGN_ROOM.bat

6. The room opens at:
   http://127.0.0.1:8776

PRIVATE OUTPUT

Z:\FOXAI\Projects\NecroscopeCampaign\CampaignRoomV1

Files include:

- campaign_state.json
- session_log.jsonl
- agent_deck_state.json
- archived states after reset

SAFETY

- Binds only to localhost.
- Does not alter source PDFs.
- Does not alter the SQLite source index.
- Does not alter the main FOXAI WebUI.
- Does not install packages.
- Uses only the already-running local model endpoint.
- Does not require internet access.
- Campaign resets archive existing state first.

V1 LIMITS

- The original FOXAI Story Deck is a proxy, not the exact MasterDeck.
- Custom point-buy character creation is not yet implemented.
- Quick-start roles are intended for immediate test play.
- Maps and image-only corebook pages are not yet visually indexed.
- Model citations are constrained to retrieved pages, but local models can still
  make mistakes; the UI also displays which pages were retrieved for each turn.

TEST PLAN

1. Start with Fast Talk for responsiveness.
2. Save a character and press Start First Scene.
3. Play three turns and confirm a background deck check occurs.
4. Use the MasterBook roller once.
5. Reveal the deck state and inspect the session log.
6. Try the same opening with Creative Brain for richer atmosphere.
