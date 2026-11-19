import './ui/styles.css';
import { App } from './core/app';

new App().start().catch((e) => {
  const fail = document.getElementById('fail');
  const msg = document.getElementById('failmsg');
  if (fail && msg) { document.getElementById('loading')?.classList.add('hidden'); msg.textContent = `Unexpected error: ${(e as Error).message}`; fail.classList.remove('hidden'); }
  console.error(e);
});
