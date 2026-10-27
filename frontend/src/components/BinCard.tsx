import { CLASSES, FULL_THRESHOLD } from '../constants';
import type { WasteClass } from '../types';

interface Props {
  type: WasteClass;
  fill: number;
  active: boolean;
  onEmpty: () => void;
}

export function BinCard({ type, fill, active, onEmpty }: Props) {
  const { name, Icon } = CLASSES[type];
  const full = fill >= FULL_THRESHOLD;

  return (
    <div className={`card bin ${active ? 'bin--active' : ''}`}>
      <div className="bin__head">
        <Icon size={18} strokeWidth={1.5} />
        <span>{name}</span>
        {full && (
          <button className="badge badge--warn badge--button" onClick={onEmpty} title="Bölmeyi boşalt">
            Dolu · Boşalt
          </button>
        )}
      </div>
      <div className="bin__value">%{fill}</div>
      <div className="bar">
        <div className={`bar__fill ${full ? 'bar__fill--warn' : ''}`} style={{ width: `${fill}%` }} />
      </div>
    </div>
  );
}
