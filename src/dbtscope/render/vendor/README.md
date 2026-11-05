# Vendored libraries

Embedded in the page by `dbtscope --offline` (D-021); the default page loads the same bytes
from the CDN URLs. Written by `tools/vendor_libraries.py`; never edit these files by hand.
To upgrade a library: change its `Library` in `src/dbtscope/render/page.py`, then run
`uv run python tools/vendor_libraries.py` and paste the printed sha256 into `LIBRARIES`.

| File | Library | Licence | Source | sha256 |
|---|---|---|---|---|
| `d3.min.js` | d3 7.9.0 | ISC | https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js | `f2094bbf6141b359722c4fe454eb6c4b0f0e42cc10cc7af921fc158fceb86539` |
| `viz.js` | viz.js 2.1.2 | MIT | https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/viz.js | `f111f22be005ceaf625f06c5a36ba7aa27703dbc0753914559edd1c24715b6e5` |
| `full.render.js` | viz.js 2.1.2 | MIT | https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/full.render.js | `3a0aace75d0b1677a4afda3b38b7697a569a02636cb3d7a04114f2cc2a95d8d4` |
| `LICENSE-d3.txt` | d3 7.9.0 | ISC | https://cdn.jsdelivr.net/npm/d3@7.9.0/LICENSE | |
| `LICENSE-viz.js.txt` | viz.js 2.1.2 | MIT | https://cdn.jsdelivr.net/npm/viz.js@2.1.2/LICENSE | |
| `LICENSE-graphviz.txt` | Graphviz 2.40.1 (in `full.render.js`) | EPL-1.0 | https://gitlab.com/graphviz/graphviz/-/raw/2.40.1/epl-v10.txt | |
| `LICENSE-expat.txt` | Expat 2.2.5 (in `full.render.js`) | MIT | https://raw.githubusercontent.com/libexpat/libexpat/R_2_2_5/expat/COPYING | |
| `LICENSE-emscripten.txt` | Emscripten 1.37.36 (in `full.render.js`) | MIT OR NCSA | https://raw.githubusercontent.com/emscripten-core/emscripten/1.37.36/LICENSE | |
| `LICENSE-musl.txt` | musl 1.1.15 (in `full.render.js`) | MIT | https://raw.githubusercontent.com/emscripten-core/emscripten/1.37.36/system/lib/libc/musl/COPYRIGHT | |

`full.render.js` is Graphviz 2.40.1 and Expat 2.2.5 compiled with Emscripten 1.37.36 by
Viz.js 2.1.2; it holds Emscripten's runtime code (MIT OR NCSA) and the musl 1.1.15 libc
Emscripten bundles (MIT). Graphviz is under the
Eclipse Public License 1.0: its source code is available from https://graphviz.org/ and
https://gitlab.com/graphviz/graphviz (tag `2.40.1`); the offline page says so in its banner.
