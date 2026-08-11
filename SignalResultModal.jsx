import { Activity, ArrowRight, RotateCw, ShieldCheck, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { countdown } from '../utils/format';

export default function SignalResultModal({ open, signal, message, onRepeat, onNewPair, onClose }) {
  const [timer, setTimer] = useState(signal?.expires_at ? countdown(signal.expires_at) : '00:00');

  useEffect(() => {
    if (!signal?.expires_at) return undefined;
    setTimer(countdown(signal.expires_at));
    const interval = window.setInterval(() => setTimer(countdown(signal.expires_at)), 1000);
    return () => window.clearInterval(interval);
  }, [signal?.expires_at]);

  if (!open || !signal) return null;

  const isSell = signal.direction === 'PUT';
  const direction = isSell ? 'SELL' : 'BUY';
  const confidence = Math.round(Number(signal.confidence || 0) * 100);

  return (
    <div className="fixed inset-0 z-[70] flex items-end bg-black/78 px-3 pb-[calc(env(safe-area-inset-bottom,0px)+18px)] pt-[calc(env(safe-area-inset-top,0px)+76px)] backdrop-blur">
      <section className="w-full overflow-hidden rounded-lg border border-terminal-green/40 bg-terminal-card shadow-2xl">
        <div className="relative overflow-hidden border-b border-terminal-border bg-terminal-bg p-4">
          <div className={`signal-result-sheen absolute inset-y-0 right-0 w-1/2 ${isSell ? 'bg-terminal-red/15' : 'bg-terminal-green/15'}`} />
          <div className="relative flex items-start justify-between gap-3">
            <div>
              <div className="flex items-center gap-2 text-xs uppercase text-terminal-muted">
                <ShieldCheck size={14} />
                Сигнал готов
              </div>
              <h2 className="mono mt-2 text-3xl font-extrabold">{signal.asset}</h2>
              <div className="mt-1 text-sm text-terminal-muted">{signal.asset_category} · {signal.timeframe}</div>
            </div>
            <div className="flex flex-col items-end gap-2">
              <button
                type="button"
                onClick={onClose}
                className="grid h-10 w-10 place-items-center rounded-lg bg-terminal-card text-white"
                title="Закрыть сигнал"
              >
                <X size={20} />
              </button>
              <div className={`rounded-lg px-4 py-3 text-xl font-extrabold ${isSell ? 'bg-terminal-red text-white' : 'bg-terminal-green text-black'}`}>
                {direction}
              </div>
            </div>
          </div>
        </div>

        <div className="p-4">
          <div className="grid grid-cols-3 gap-2">
            <ResultStat label="Точность" value={`${confidence}%`} />
            <ResultStat label="Цена" value={signal.open_price || '-'} mono />
            <ResultStat label="Таймер" value={timer} mono />
          </div>

          <div className="mt-4 rounded-lg border border-terminal-border bg-terminal-bg p-4">
            <div className="flex items-center gap-3">
              <div className="grid h-11 w-11 place-items-center rounded-lg bg-terminal-green/10 text-terminal-green">
                <Activity size={22} />
              </div>
              <div>
                <div className="font-bold">{message || 'Анализ завершен'}</div>
                <div className="mt-1 text-sm text-terminal-muted">Индикаторы и ML-фильтр совпали по направлению.</div>
              </div>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={onRepeat}
              className="flex h-14 items-center justify-center gap-2 rounded-lg bg-terminal-green text-base font-extrabold text-black"
            >
              <RotateCw size={19} />
              Ещё раз
            </button>
            <button
              type="button"
              onClick={onNewPair}
              className="flex h-14 items-center justify-center gap-2 rounded-lg border border-terminal-border bg-terminal-bg text-base font-extrabold text-white"
            >
              Новая пара
              <ArrowRight size={19} />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

function ResultStat({ label, value, mono = false }) {
  return (
    <div className="rounded-lg border border-terminal-border bg-terminal-bg px-3 py-3">
      <div className="text-xs text-terminal-muted">{label}</div>
      <div className={`mt-1 truncate text-sm font-extrabold ${mono ? 'mono' : ''}`}>{value}</div>
    </div>
  );
}
