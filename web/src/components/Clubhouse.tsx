import type { Activity } from '../lib/types'
export function Clubhouse({ assets = [], recent, palette = 'dawn', compact = false }: { assets?: string[]; recent?: Activity; palette?: string; compact?: boolean }) {
  const bench = assets.includes('bench'), tree = assets.includes('memory-tree'), sign = assets.includes('trail-sign')
  return <div className={`clubhouse ${palette} ${compact ? 'compact' : ''}`}><svg viewBox="0 0 900 440" role="img" aria-label={`강가의 우리 클럽하우스. ${bench ? '함께 만든 벤치, ' : ''}${tree ? '기념 나무, ' : ''}${sign ? '첫 이정표가 있어요.' : '함께할 시간을 기다려요.'}`}>
    <defs><pattern id="water" width="90" height="18" patternUnits="userSpaceOnUse"><path d="M5 8h24m25 7h16" fill="none" stroke="currentColor" strokeWidth="2" opacity=".15"/></pattern></defs>
    <rect width="900" height="440" className="scene-sky"/><circle cx="725" cy="76" r="35" className="scene-sun"/>
    <path d="M0 170Q115 105 240 162T500 142T900 130V300H0Z" fill="var(--color-meadow)" opacity=".65"/>
    <path d="M0 215Q145 150 280 204T540 195T900 181V440H0Z" fill="var(--color-primary)" opacity=".12"/>
    <path d="M0 255Q230 208 450 244T900 218V440H0Z" className="scene-river"/><path d="M0 255Q230 208 450 244T900 218V440H0Z" fill="url(#water)"/>
    <path d="M0 324Q200 233 440 286T900 281V440H0Z" className="scene-ground"/>
    <path d="M153 440Q228 354 430 347T754 440" stroke="var(--color-background)" strokeWidth="54" fill="none" opacity=".8"/>
    <g transform="translate(120 127)" fill="var(--color-primary)"><path d="M0 170V65" stroke="currentColor" strokeWidth="10"/><path d="M-55 80Q-65-5 3 0Q64 5 52 85Q0 119-55 80" opacity=".75"/><path d="M-38 115Q-53 47 10 47Q55 50 47 108Q9 142-38 115"/></g>
    <g transform="translate(355 140)"><ellipse cx="108" cy="177" rx="136" ry="18" fill="var(--color-primary)" opacity=".13"/><path d="M0 60h220v105H0Z" fill="var(--color-surface)"/><path d="M-20 65 107-12 240 65Z" fill="var(--color-clay)"/><path d="m4 54 103-61 106 61" stroke="var(--color-ink)" opacity=".2" strokeWidth="3" fill="none"/><path d="M88 95h44v70H88Z" fill="var(--color-primary)"/><circle cx="121" cy="130" r="2" fill="var(--color-meadow)"/>
      <g fill={recent?.visible ? 'var(--color-meadow)' : 'var(--color-sky)'} stroke="var(--color-primary)" strokeWidth="3"><rect x="22" y="88" width="43" height="43" rx="2"/><rect x="158" y="88" width="43" height="43" rx="2"/></g><path d="M43 88v43m-21-22h43m114-21v43m-21-22h43" stroke="var(--color-primary)" strokeWidth="2"/><path d="M-6 165h232v13H-6Z" fill="var(--color-clay)"/><rect x="67" y="55" width="85" height="22" rx="3" fill="var(--color-background)"/><text x="110" y="70" textAnchor="middle" fontSize="11" fontWeight="700" fill="var(--color-primary)" fontFamily="var(--font-display)">OUR CLUBHOUSE</text>
    </g>
    {bench && <g transform="translate(620 315)" stroke="var(--color-clay)" strokeWidth="9" strokeLinecap="round"><path d="M0 0h90M0 13h90M10 13v22m70-22v22M10-10v10m70-10v10"/><path d="M1 24h88" strokeWidth="6"/></g>}
    {sign && <g transform="translate(263 305)"><path d="M0 0v68" stroke="var(--color-clay)" strokeWidth="7"/><path d="M-34 0h71l12 13-12 13h-71Z" fill="var(--color-primary)"/><path d="M-19 13H23m-8-5 8 5-8 5" stroke="var(--color-background)" strokeWidth="2" fill="none"/></g>}
    {tree && <g transform="translate(774 222)"><path d="M0 40v105" stroke="var(--color-clay)" strokeWidth="9"/><circle cx="-22" cy="32" r="34" fill="var(--color-primary)"/><circle cx="22" cy="31" r="39" fill="var(--color-primary)"/><circle cy="0" r="37" fill="var(--color-primary)"/><circle cx="-12" cy="-8" r="3" fill="var(--color-meadow)"/><circle cx="22" cy="26" r="3" fill="var(--color-meadow)"/></g>}
    <g fill="var(--color-primary)" opacity=".4"><path d="m60 375 4-16 5 16m46 25 4-16 5 16m689-5 4-16 5 16m-103-18 4-16 5 16"/></g>
    <path d="m248 92 9-5 9 5m-25 17 7-4 7 4" fill="none" stroke="var(--color-primary)" strokeWidth="2" opacity=".4"/>
  </svg><div className="scene-caption"><span className="small-sun" aria-hidden="true"/><span>{recent?.label || '우리만의 편안한 시간'}</span><span className="scene-period">{recent?.period || '보호된 대화 분위기'}</span></div></div>
}
