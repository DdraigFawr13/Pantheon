---
id: factions
type: factions
visibility: public
tags: [factions, realms, politics, clocks, tallyhouse]
---

# Factions and Global Clocks

## Realms and orders

### The Hale Kingdoms (Veshra)

- **Region:** the fertile central plains and river valleys. **Capital:** Halewick.
- **Government:** feudal monarchy bound by the **Assize**: courts where sworn testimony is Ledger-witnessed.
- **Highest tier present:** Tier 5 (Lord Justiciar Aldemar Voss).
- **Goals:** restore the Pact; legitimize an Heir from within the Assize.
- **Tension:** the crown wants to fill the Seat with its own candidate; the Assize wants a candidate chosen by law.

### The Ironmarch (Kaul)

- **Region:** northern hills and forge-cities. **Capital:** Kaulgard.
- **Government:** confederation of warlords; the Warlord Moot elects a High Hammer every seven years.
- **Highest tier present:** Tier 5 (High Hammer Brenna Oakhelm).
- **Goals:** a standing army tested by Delves; expansion toward the southern grain lands.
- **Tension:** the Moot is split between war with Hale and consolidation.

### The League of Seven Harbors (Ysmere, Drovash)

- **Region:** the southern coast. **Largest port:** Saltmere.
- **Government:** merchant republic; seven Harbor-Houses vote by tonnage.
- **Highest tier present:** Tier 4.
- **Goals:** open trade; resist both Hale tariffs and Ironmarch conscription.
- **Tension:** the Houses disagree about whether to tolerate or suppress the Underlanes.

### The Antler Wilds (Hurrow)

- **Region:** the western forests and fens. No cities.
- **Government:** clan hunt-moots, no central authority.
- **Highest tier present:** Tier 5 (the Elder Stag, a beast-sovereign of ambiguous personhood).
- **Goals:** halt road and wall expansion into the forest.
- **Tension:** young clans want to raid; elder clans want truce.

### The Ashen Convent (Maru-Ghen)

- **Region:** the Barrow-Lands (eastern moors). **Seat:** Sorrowfield.
- **Government:** a Conclave of Grave-Wardens.
- **Highest tier present:** Tier 4.
- **Goals:** bury the dead properly; destroy undeath; hold the line against Delve-spawned dead.
- **Tension:** pragmatists accept necromantic tools against Delve threats; purists forbid it.

### The Lantern Orders (Ilvane)

- **Region:** the Candle Peaks. **Seat:** the monastery-city Halcyr.
- **Government:** a council of Seers; rank by accuracy of prophecy.
- **Highest tier present:** Tier 5 (Seer-Prime Oriel Wren).
- **Goals:** publicly, to guide. Selling prophecy funds the Orders.
- **Tension:** disputed whether prophecy should be sold to realms at war.

### The Underlanes (Drovash)

- **Region:** every city. A network of thieves, smugglers, fences, and information brokers.
- **Government:** informal; seven **Keyholders** hold regional keys.
- **Highest tier present:** Tier 4.
- **Goals:** keep the Pact from returning; preserve the freedom to operate.
- **Tension:** the Keyholders disagree about open war with the Assize.

### The Tallyhouse (neutral guild)

- **Region:** every city of size. Certifies tiers, registers Delvers, posts bounties.
- **Government:** a Board of Tally from four Houses; hereditary Registrars.
- **Highest tier present:** Tier 3 (field staff); Tier 5 (Grand Registrar).
- **Goals:** neutrality, profit, and keeping every Delve cleared on schedule.
- **Tension:** quiet disputes about who benefits from unrecorded Delves.

## Global clocks

A clock has a fixed number of segments. The narrator may request `advance_clock`; the engine accepts only when the story supports it. Clocks also advance with elapsed time.

| Clock | Segments | Filled consequence |
|---|---|---|
| **The Seat Vote** | 6 | The council moves to a formal vote on an Heir. Each segment reflects shifting god positions. |
| **The Delve Tide** | 8 | An **Overflow**: a major Delve breaks its seal and spills monsters into a settled region. |
| **The Grain War** | 6 | Open war between the Ironmarch and the Hale Kingdoms. |
| **The Ember Fever** | 5 | A plague tied to a Delve source; the Ashen Convent quarantines a region. |
| **The Lantern's Price** | 4 | A prophecy comes due; Ilvane collects. |

Start state: Seat Vote 1, Delve Tide 2, Grain War 2, Ember Fever 0, Lantern's Price 0.

## Relationships (starting Standing between factions, -100 to +100)

| | Hale | Ironmarch | Harbors | Wilds | Convent | Lantern | Underlanes | Tallyhouse |
|---|---|---|---|---|---|---|---|---|
| Hale | n/a | -15 | 10 | -20 | 25 | 10 | -50 | 20 |
| Ironmarch | -15 | n/a | -10 | -35 | 5 | 0 | -40 | 25 |
| Harbors | 10 | -10 | n/a | 0 | 0 | 5 | 20 | 30 |
| Wilds | -20 | -35 | 0 | n/a | 15 | 10 | 0 | -10 |
| Convent | 25 | 5 | 0 | 15 | n/a | 15 | -30 | 10 |
| Lantern | 10 | 0 | 5 | 10 | 15 | n/a | 5 | 15 |
| Underlanes | -50 | -40 | 20 | 0 | -30 | 5 | n/a | -15 |
| Tallyhouse | 20 | 25 | 30 | -10 | 10 | 15 | -15 | n/a |
