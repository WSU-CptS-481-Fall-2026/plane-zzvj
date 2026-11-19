# Reproducing the filtering baseline

From the repository root, define the shell arrays in the [filtering test guide](../../../../apps/api/tests/RUNNING_TESTS.md#deliverable-2-filtering-regression-suite). In the same shell, export the starting revision to a temporary directory.

```bash
filter_snapshot=$(mktemp -d)
git archive e4f4bd728200c0ae7336e50b68d634ede919feae apps/api docker-compose-test.yml | tar -x -C "$filter_snapshot"
cp "$filter_snapshot/apps/api/.env.example" "$filter_snapshot/apps/api/.env"
```

1. **Original baseline.** In the export, run the guide's coverage command using the four original test files listed in the [manifest](manifest.json). Save the results.
2. **Expanded baseline.** From the current repository root, copy the seven test files into the export. Run the seven-file coverage command inside the export and save its results separately.

   ```bash
   for file in "${filter_tests[@]}"; do
     cp "apps/api/$file" "$filter_snapshot/apps/api/$file"
   done
   ```

3. **After modernization.** From the current repository root, copy the three production modules listed in the [report](../README.md) to their matching paths in the export. Run the same seven-file coverage command there and save the final results.

For complexity at any stage, install `radon==6.0.1` in an isolated Python environment and run the following from the current repository root.

```bash
python contributions/zuriel/deliverable-2/evidence/measure.py "$filter_snapshot/apps/api"
```
