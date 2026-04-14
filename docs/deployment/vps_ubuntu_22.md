# Ubuntu 22.04 VPS Deployment

## First deployment
- install docker + docker compose plugin
- clone repo to `/opt/ai-trading-system`
- copy `.env.example` to `.env` and fill secrets
- run `./infra/scripts/deploy.sh develop`

## Update deployment
- run `./infra/scripts/deploy.sh <branch>`

## Rollback
- run `./infra/scripts/rollback.sh <git-ref>`

## Migration
- run `./infra/scripts/migrate.sh`

## Health verification
- run `./infra/scripts/healthcheck.sh`

## Backups and logs
- mount postgres volume snapshots daily
- keep `/var/lib/docker/volumes/*pgdata*` backup
- centralize container logs to `/var/log/ai-trading/` via docker logging driver (stage 2 hardening)
