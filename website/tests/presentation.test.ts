import { describe, expect, it } from 'vitest';
import { GROUP_NAME, readableSourceText, researchTooltipStyles } from '../src/lib/presentation';

describe('readable research presentation', () => {
  it('uses the confirmed group name', () => {
    expect(GROUP_NAME).toBe('Group 5 xam.py');
  });
  it('preserves explicit synthetic provenance without changing the source', () => {
    const source = 'Synthetic cable system id';
    expect(readableSourceText(source)).toBe('Synthetic cable system id');
    expect(source).toBe('Synthetic cable system id');
  });
  it('retains the publisher qualification including parentheses', () => {
    expect(
      readableSourceText('100% computer-generated (synthetic) dataset; not a verified registry.'),
    ).toBe('100% computer-generated (synthetic) dataset; not a verified registry.');
  });
  it('gives tooltip headers and values high contrast on the dark surface', () => {
    const luminance = (hex: string) => {
      const rgb = hex
        .replace('#', '')
        .match(/../g)!
        .map((value) => {
          const n = parseInt(value, 16) / 255;
          return n <= 0.04045 ? n / 12.92 : ((n + 0.055) / 1.055) ** 2.4;
        });
      return rgb[0] * 0.2126 + rgb[1] * 0.7152 + rgb[2] * 0.0722;
    };
    const background = luminance(researchTooltipStyles.contentStyle.backgroundColor);
    for (const color of [
      researchTooltipStyles.labelStyle.color,
      researchTooltipStyles.itemStyle.color,
    ]) {
      expect((luminance(color) + 0.05) / (background + 0.05)).toBeGreaterThan(7);
    }
  });
});
