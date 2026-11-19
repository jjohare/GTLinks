# Front-end evidence (web/)

Screenshots taken in the browser-gpu sidecar against `http://agentbox:8795/gtlinks/` (the built `dist` served from
a sub-path). `real-*` frames are the shipped build running the real wasm simulation: `real-webgpu-*` on the WebGPU
backend, `real-webgl-*` with `?renderer=webgl` (backend confirmed from `window.__gtlinks.backend`). The steins in
those runs were loaded with trusted CDP mouse events (`Input.dispatchMouseEvent`). `standin-sim-build/` holds earlier
frames from before the wasm package landed (real GLBs, stand-in simulation); they are kept only as history.
