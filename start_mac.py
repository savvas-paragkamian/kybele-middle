"""Configure Metal inference and start the Mac API gateway (run from any cwd)."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
COMPOSE = ['docker', 'compose', '-f', 'compose.mac.yaml']


def run(*args, **kwargs):
    return subprocess.run(args, cwd=ROOT, check=True, **kwargs)


def main():
    # Compose resolves .env without executing it or printing credentials.
    config = json.loads(run(*COMPOSE, 'config', '--format', 'json',
                            capture_output=True, text=True).stdout)
    model = config['services']['llm']['environment']['MODEL_ID']
    run('docker', 'model', 'status')
    available = subprocess.run(['docker', 'model', 'inspect', model], cwd=ROOT,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if available.returncode:
        run('docker', 'model', 'pull', model)
    run('docker', 'model', 'configure', '--context-size', '8192', '--think=false', model, '--',
        '--n-gpu-layers', '99', '--parallel', '1', '--jinja')
    run(*COMPOSE, 'up', '-d', '--build')


if __name__ == '__main__':
    main()
