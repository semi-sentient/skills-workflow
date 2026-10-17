source "$FIXTURE_DIR/../../lib.sh"
init_repo
stage_bands_clean
mkdir -p scripts
cat > scripts/check-bands.js <<'EOF'
import { bandForRate } from '../src/bands.js';

const cases = [[5, 5, 'green'], [3.5, 5, 'amber'], [0, 5, 'red']];
for (const [rate, target, want] of cases) {
  if (bandForRate(rate, target) !== want) {
    console.error(`bandForRate(${rate}, ${target}) !== ${want}`);
    process.exit(1);
  }
}
console.log('bands ok');
EOF
git add -A
