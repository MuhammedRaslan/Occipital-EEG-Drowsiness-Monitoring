# Figure numbering — findings and the exact edits to make

I read `submission/main.tex` but did not modify it, since you are editing it in
another session. This file is the hand-off: what I found, and the edits to apply
there.

## What is actually wrong

Not the printed numbers. Every figure and table in the manuscript is referenced
through `\ref{}`, and every `\label` is unique, so LaTeX assigns the printed
numbers itself and they cannot drift out of sync with the text.

What is wrong is the **filenames**. They are legacy analysis-pipeline names
(`fig10`–`fig14`) left over from before figures were removed, and they no longer
correspond to anything. `fig13` is printed as Fig. 1, `fig10` as Fig. 3. That
matters at upload time: the Author Portal takes figures as individual files in
figure order, and IEEE production staff match file to figure by name. A file
called `fig10` sitting in the Figure 3 slot is how figures end up transposed in
the proofs.

I also confirmed the ordering is otherwise sound:

- **Citation order is correct.** Every figure and table is first referenced in
  the body before it is defined, and in the same sequence it is defined.
- **No hard-coded numbers.** There is no literal `Fig. 3` or `Table IV` typed
  into the prose anywhere — searched, zero matches. So nothing breaks if a
  number shifts.

## The mapping

| Printed as | `\label` | Current filename | Renamed to |
|---|---|---|---|
| Fig. 1 | `fig:coh` | `fig13_coherence_separation.png` | `fig1_coherence_separation.png` |
| Fig. 2 | `fig:ema` | `fig14_ema_raw_vs_smoothed.png` | `fig2_ema_raw_vs_smoothed.png` |
| Fig. 3 | `fig:roc` | `fig10_v17_roc.png` | `fig3_roc.png` |
| Fig. 4 | `fig:severity` | `fig11_lead_vs_severity.png` | `fig4_lead_vs_severity.png` |
| Fig. 5 | `fig:demo` | `fig12_live_demo.png` | `fig5_live_demo.png` |

The renamed, RGB-flattened files are in `submission_ready/figures/`.

## The five edits to apply in your session

Line numbers are as of my read and will have shifted if you have been editing —
match on the filename, which is unique in each case.

| Was (line) | Change to |
|---|---|
| 332 | `\includegraphics[width=\columnwidth]{fig1_coherence_separation.png}` |
| 368 | `\includegraphics[width=\columnwidth]{fig2_ema_raw_vs_smoothed.png}` |
| 378 | `\includegraphics[width=\columnwidth]{fig3_roc.png}` |
| 533 | `\includegraphics[width=\columnwidth]{fig4_lead_vs_severity.png}` |
| 569 | `\includegraphics[width=\textwidth]{fig5_live_demo.png}` |

Nothing else changes — no `\label`, no `\ref`, no caption.

## One thing I could not check: full-width table placement

Six of the ten tables are `table*` (full-width) floats: `tab:roc`,
`tab:persubj`, `tab:cross`, `tab:proactive`, `tab:severity`, `tab:compare`.

In IEEEtran's two-column mode a `table*` can only be set at the top of a page,
so LaTeX often defers it past one or more single-column floats. A float is
numbered when it is *placed*, not where it is defined — so a deferred `table*`
can end up with a higher number than a single-column `table` that was defined
after it. The likely candidate here is `tab:roc` (a `table*`, defined before the
single-column `tab:paired`).

The `\ref`s stay correct either way, so no claim in the text becomes wrong. What
breaks is IEEE's expectation that floats *appear* in citation order, which a
copy-editor will flag.

I could not verify this: there is no TeX installation on this machine
(`pdflatex` is not on PATH), so I could not compile. **When you next build the
PDF, read the table numbers in the order they appear on the page.** If they run
out of sequence, the usual fix is to move the offending `table*` block earlier in
the source, or to promote a neighbouring single-column `table` to `table*` so
both defer together.
