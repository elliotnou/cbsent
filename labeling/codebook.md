# Labeling Codebook: Hawkish-Dovish Stance and Topic

Version 1, drafted for review. Every labelled sentence gets exactly one
stance label and one topic label. When in doubt, follow the decision rules
below; when still in doubt, label neutral and flag for adjudication.

## Sources

The scheme adapts:

- Shah, Paturi & Chava (2023), "Trillion Dollar Words: A New Financial
  Dataset, Task & Market Analysis", ACL 2023 — sentence-level
  hawkish/dovish/neutral/irrelevant annotation of FOMC text; our stance
  definitions and several decision rules follow their annotation guide.
- Apel & Blix Grimaldi (2012), "The Information Content of Central Bank
  Minutes", Sveriges Riksbank Working Paper No. 261 — the
  hawkish/dovish dictionary tradition; their term taxonomy informs our
  keyword-independent definitions (label meaning, not keywords).
- Picault & Renault (2017), "Words are not all created equal: A new measure
  of ECB communication", Journal of International Money and Finance —
  separating monetary-policy stance from economic-outlook content.
- Hansen & McMahon (2016), "Shocking language: Understanding the
  macroeconomic effects of central bank communication", Journal of
  Monetary Economics — topic structure of FOMC communication.

## Unit

One sentence (as produced by `cbsent.segment`). Label the sentence in the
context of the document it came from, but do not import stance from
neighbouring sentences: if the sentence alone would not tell a reader the
direction of policy, it is neutral.

## Stance labels

**hawkish** — the sentence, read alone, signals tighter policy or pressure
toward tighter policy: rate increases (delivered, likely, or advocated),
inflation running above target or risks to inflation tilted upward, an
overheating economy or labour market described as a pressure on prices,
balance sheet runoff, or explicit commitment to restrictive conditions.

**dovish** — the sentence signals easier policy or pressure toward easier
policy: rate cuts (delivered, likely, or advocated), inflation returning to
or undershooting target, economic weakness or slack that argues for
accommodation, asset purchases, or commitment to maintaining stimulus.

**neutral** — everything else: process descriptions, balanced risk
assessments, data recitations with no directional policy implication,
boilerplate about mandates and voting.

### Decision rules

1. **Negation flips or voids the surface reading.** "It is not yet
   appropriate to raise rates" is NOT hawkish — the modal content is
   "no hike now", which is dovish-to-neutral (label: dovish if it signals
   holding at low rates, neutral if purely procedural). "The Committee does
   not expect further increases will be necessary" is dovish despite
   containing "increases".
2. **Hedges weaken but do not flip.** "Some further tightening may be
   appropriate" is hawkish (hedged, still directional). "The Committee will
   monitor incoming data" is neutral — pure optionality with no direction.
3. **Direction of the economy is not direction of policy.** "GDP growth
   slowed in the fourth quarter" is dovish only if weakness argues for
   easing in context of the central bank's reaction function; a bare data
   recitation with no policy-relevant framing is neutral. When the sentence
   frames the data as a pressure on the policy path ("growth remains above
   trend, adding to inflationary pressure"), label by the implied policy
   direction.
4. **Past actions carry their direction.** "The Committee decided to raise
   the target range by 75 basis points" is hawkish; "decided to lower" is
   dovish; "decided to maintain" is neutral unless paired with directional
   guidance in the same sentence.
5. **Inflation praise is dovish, inflation alarm is hawkish.** "Inflation
   has eased substantially over the past year" is dovish (less pressure to
   tighten). "Inflation remains elevated" is hawkish.
6. **Financial stability worries are not automatically dovish.** Label by
   the policy implication stated in the sentence, else neutral.
7. **Conditional promises follow their condition's direction.** "If the
   economy evolves as expected, it will likely be appropriate to begin
   dialing back policy restraint this year" is dovish.

### Worked negation/hedge examples

| Sentence | Label | Why |
|---|---|---|
| "It is not yet appropriate to raise the target range." | dovish | Negated hike = holding at accommodation. |
| "The Committee does not anticipate reducing the policy rate until it has gained greater confidence that inflation is moving sustainably toward 2 percent." | hawkish | Negated cut = restrictive for longer. |
| "Some further policy firming may be appropriate." | hawkish | Hedged but directional. |
| "The Committee is prepared to adjust the stance of monetary policy as appropriate if risks emerge." | neutral | Pure optionality, no direction. |
| "Inflation is no longer broad-based." | dovish | Negated inflation pressure. |
| "The labour market is not overheated." | dovish | Negated tightening pressure. |
| "Members judged that a further modest reduction in the policy rate could be warranted, though they did not commit to a timetable." | dovish | Hedge does not flip the cut signal. |

## Topic labels

One of five: **inflation**, **employment**, **growth**,
**financial_stability**, **guidance**. If a sentence spans several, choose
the one carrying the stance; if neutral, the dominant subject.

- **inflation** — price developments, expectations, target progress.
- **employment** — labour market conditions, wages, maximum employment.
- **growth** — output, demand, consumption, investment, trade, global
  conditions.
- **financial_stability** — credit conditions, banking system, market
  functioning, household debt, housing imbalances.
- **guidance** — the policy decision itself, forward guidance, balance
  sheet policy, reaction function, voting.

(The retired 5-class scheme's "Boilerplate" is now expressed through the
stance label: procedural sentences are neutral, and topic still records
what they are about. Sentences with no monetary-policy content at all —
scheduling notes, publication footers — should have been removed upstream;
if one appears, label neutral / guidance and flag it.)

## Stratification note for review

The review queue serves sentences in stratified order: all bootstrap
disagreements (dictionary vs LLM), then a random sample per
(bank, year, bootstrap label) cell. Reviewer decisions are final.
