name: Deploy Range Config

on:
  push:
    paths:
      - 'ludus-range-config.yml'
      - 'roles/**'
  workflow_dispatch:

jobs:
  deploy_range:
    runs-on: ubuntu-latest
    timeout-minutes: 180
    permissions:
      contents: write
    env:
      LUDUS_API_KEY: ${{ secrets.LUDUS_API_KEY }}
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
        with:
          persist-credentials: true
          fetch-depth: 0

      - name: Validate and Format YAML Config
        run: |
          echo "Validating YAML syntax (initial run)..."
          # Run initial validation; warnings/errors are printed
          yamllint ludus-range-config.yml || true

          echo "Removing trailing whitespace..."
          sed -i 's/[[:space:]]*$//' ludus-range-config.yml

          echo "Installing latest yq for YAML reformatting..."
          # Download the latest go-based yq binary (v4)
          wget https://github.com/mikefarah/yq/releases/download/v4.45.1/yq_linux_amd64 -O /usr/local/bin/yq
          chmod +x /usr/local/bin/yq

          echo "Reformatting YAML file using yq..."
          yq eval . -i ludus-range-config.yml

          echo "Re-validating YAML syntax with custom configuration..."
          # Use a custom yamllint configuration: disable document-start and trailing-spaces;
          # allow longer lines (max 120 characters) with warnings.
          yamllint --config-data "{extends: default, rules: {document-start: disable, trailing-spaces: disable, line-length: {max: 120, level: warning}}}" ludus-range-config.yml

      - name: Install WireGuard & jq
        run: |
          sudo apt-get update -y
          sudo apt-get install -y wireguard jq

      - name: Write WireGuard Config
        shell: bash
        env:
          WIREGUARD_CONFIG: ${{ secrets.WIREGUARD_CONFIG }}
        run: |
          echo "$WIREGUARD_CONFIG" | base64 --decode > wg0.conf
          chmod 600 wg0.conf

      - name: Activate WireGuard VPN
        run: sudo wg-quick up ./wg0.conf

      - name: Install Ludus CLI Non-Interactively
        run: |
          set -e
          # Ensure 'script' command is available
          if ! command -v script >/dev/null; then
            echo "Error: 'script' command not found. Aborting."
            exit 1
          fi
          # Install Ludus CLI non-interactively
          script -q -c 'printf "y\ny\ny\n" | curl -s https://ludus.cloud/install | bash' /dev/null

      - name: Add Ludus CLI to PATH
        run: echo "/usr/local/bin" >> $GITHUB_PATH

      - name: Validate Ludus API Key
        run: |
          set -e
          if [ -z "$LUDUS_API_KEY" ]; then
            echo "Error: LUDUS_API_KEY is not set!"
            exit 1
          fi
          echo "LUDUS_API_KEY is set."

      - name: Deploy Ludus Range
        run: |
          set -e
          # Set the configuration and initiate deployment.
          ludus range config set -f ./ludus-range-config.yml
          ludus range deploy

          # Wait until the deployment is no longer in the "DEPLOYING" state.
          echo "Waiting for deployment to finish..."
          while [[ "$(ludus range status --json | jq -r '.rangeState')" == "DEPLOYING" ]]; do
            sleep 10
          done

          # Capture the final state.
          FINAL_STATE=$(ludus range status --json | jq -r '.rangeState')
          echo "Final deployment state: ${FINAL_STATE}"

          # Display logs and exit accordingly.
          if [[ "${FINAL_STATE}" == "SUCCESS" ]]; then
            echo "Deployment succeeded. Displaying logs:"
            ludus range logs
          else
            echo "Deployment failed or ended in an unexpected state. Displaying logs:"
            ludus range logs
            exit 1
          fi

      - name: Disconnect WireGuard
        if: always()
        run: |
          if [ -f wg0.conf ]; then
            sudo wg-quick down ./wg0.conf
          else
            echo "wg0.conf not found. Skipping disconnect."
          fi

      - name: Run Python Script to update README.md range-config
        env:
          LUDUS_INPUT_FILE: ludus-range-config.yml
          LUDUS_OUTPUT_FILE: README.md
        run: python3 ludus-range-config.py

      - name: Commit and push updated README.md
        run: |
          git config --global user.email "action@github.com"
          git config --global user.name "GitHub Action"
          git add config/ludus/README.md
          git commit -m "Update README.md via Python script" || echo "No changes to commit"
          git push
