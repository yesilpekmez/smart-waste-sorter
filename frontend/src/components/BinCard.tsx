import { CLASSES } from '../constants';
import type { WasteClass } from '../types';

interface Props {
  type: WasteClass;
  fill: number | null; // null: henüz okunmadı
  fullThreshold?: number;
  active: boolean;
  // Yalnızca simülasyonda; gerçek bölme elle boşaltılır
  onEmpty?: () => void;
}

export function BinCard({ type, fill, fullThreshold, active, onEmpty }: Props) {
  const { name, Icon } = CLASSES[type];
  const full = fill !== null && fullThreshold !== undefined && fill >= fullThreshold;

  return (
    <div className={`card bin ${active ? 'bin--active' : ''}`}>
      <div className="bin__head">
        <Icon size={18} strokeWidth={1.5} />
        <span>{name}</span>
        {full &&
          (onEmpty ? (
            <button className="badge badge--warn badge--button" onClick={onEmpty} title="Simülasyonda bölmeyi boşalt">
              Dolu · Boşalt
            </button>
          ) : (
            <span className="badge badge--warn badge--button">Dolu</span>
          ))}
      </div>
      <div className={`bin__value ${fill === null ? 'muted' : ''}`}>{fill === null ? '—' : `%${fill}`}</div>
      <div className="bar">
        <div className={`bar__fill ${full ? 'bar__fill--warn' : ''}`} style={{ width: `${fill ?? 0}%` }} />
      </div>
    </div>
  );
}
