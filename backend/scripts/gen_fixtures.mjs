// 프론트 engine(compare.ts) 출력을 fixtures로 떠서 백엔드 동치 테스트에 사용.
// 실행: cd backend && TZ=UTC npx tsx scripts/gen_fixtures.mjs
//   (tsx: TS를 node에서 바로 실행. 프론트 node_modules 설치 불필요 — compare.ts는 순수)
//
// now(new Date())를 고정해 결정론적으로 만든다. Python 테스트는 이 now로 비교한다.
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const enginePath = resolve(__dirname, '../../frontend/src/engine/compare.ts');
const outPath = resolve(__dirname, '../tests/fixtures/compare_cases.json');

// ── now 고정 (currentDate와 동일) ──────────────────────────────────
const FIXED_ISO = '2026-07-19T00:00:00.000Z';
const RealDate = Date;
const FIXED = new RealDate(FIXED_ISO).getTime();
class MockDate extends RealDate {
  constructor(...args) {
    if (args.length === 0) super(FIXED);
    else super(...args);
  }
  static now() { return FIXED; }
}
globalThis.Date = MockDate;

const { compare } = await import(pathToFileURL(enginePath).href);

// ── 테스트 케이스 (전세/월세 × 미사용/사용/모름 커버) ───────────────
const cases = [
  {
    name: 'P1 전세 사회초년생 미사용',
    contract: { type: '전세', deposit: 200000000, monthlyRent: 0, expiryDate: '2026-11-19', renewalUsed: '미사용' },
    finance: { annualIncome: 40000000, ownCapital: 30000000, household: '1인', firstHome: '모름', under35: true },
  },
  {
    name: 'P2 신혼 전세 3.2억 미사용',
    contract: { type: '전세', deposit: 320000000, monthlyRent: 0, expiryDate: '2026-10-30', renewalUsed: '미사용' },
    finance: { annualIncome: 80000000, ownCapital: 60000000, household: '신혼', firstHome: '예', under35: true },
  },
  {
    name: 'P3 월세 2천/80 모름',
    contract: { type: '월세', deposit: 80000000, monthlyRent: 2000000, expiryDate: '2026-12-19', renewalUsed: '모름' },
    finance: { annualIncome: 55000000, ownCapital: 15000000, household: '1인', firstHome: '아니오', under35: true },
  },
  {
    name: 'P4 전세 갱신권 사용 (경계)',
    contract: { type: '전세', deposit: 250000000, monthlyRent: 0, expiryDate: '2026-09-30', renewalUsed: '사용' },
    finance: { annualIncome: 50000000, ownCapital: 20000000, household: '신혼', firstHome: '모름', under35: true },
  },
  {
    name: 'P5 월세 미사용 (경계)',
    contract: { type: '월세', deposit: 50000000, monthlyRent: 800000, expiryDate: '2026-08-30', renewalUsed: '미사용' },
    finance: { annualIncome: 45000000, ownCapital: 5000000, household: '1인', firstHome: '예', under35: false },
  },
  {
    name: 'P6 전세 빌라(연립다세대) — HUG 요율 분기',
    contract: { type: '전세', deposit: 200000000, monthlyRent: 0, expiryDate: '2026-11-19', renewalUsed: '미사용', housingType: '빌라' },
    finance: { annualIncome: 40000000, ownCapital: 30000000, household: '1인', firstHome: '모름', under35: true },
  },
];

const out = {
  now: FIXED_ISO,
  generatedFrom: 'KB만기상담소2/src/engine/compare.ts',
  cases: cases.map((c) => ({ ...c, expected: compare(c.contract, c.finance) })),
};

mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, JSON.stringify(out, null, 2) + '\n', 'utf-8');
console.log(`✓ ${out.cases.length} cases → ${outPath}`);
