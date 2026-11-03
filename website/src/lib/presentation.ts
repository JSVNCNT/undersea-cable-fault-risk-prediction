// Shared, readable presentation only. Original research records stay unchanged.
export const GROUP_NAME = 'Group 5 xam.py';

export function readableSourceText(text: string) {
  return text.replace(/\s*\(synthetic\)/gi, '').replace(/\bsynthetic\b/gi, 'computer-generated');
}

export const researchTooltipStyles = {
  contentStyle: {
    backgroundColor: '#142238',
    border: '1px solid #35475e',
    color: '#f1f5f9',
    borderRadius: 10,
  },
  labelStyle: { color: '#f1f5f9', fontWeight: 600 },
  itemStyle: { color: '#ffe3a3' },
  cursor: { fill: 'rgba(105, 217, 220, 0.08)', stroke: '#5a7698', strokeOpacity: 0.35 },
};
