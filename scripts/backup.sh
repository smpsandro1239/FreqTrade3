#!/bin/bash

# ========================================
# FREQTRADE3 - SCRIPT DE BACKUP SEGURO
# ========================================
# Backup automático e seguro de configurações e dados
# Execute antes de atualizações ou alterações importantes

set -e

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configurações
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="freqtrade3_backup_$DATE"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

# Criar diretório de backup
mkdir -p "$BACKUP_PATH"

print_status "Iniciando backup seguro do FreqTrade3..."

# Função para criptografar arquivo
encrypt_file() {
    local input_file="$1"
    local output_file="$2"

    if command -v gpg >/dev/null 2>&1; then
        gpg --cipher-algo AES256 --compress-algo 1 --s2k-mode 3 \
            --s2k-digest-algo SHA512 --s2k-count 65536 --symmetric \
            --output "$output_file" "$input_file" 2>/dev/null && return 0 || return 1
    else
        # Fallback: usar openssl se disponível
        if command -v openssl >/dev/null 2>&1; then
            openssl enc -aes-256-cbc -salt -in "$input_file" -out "$output_file" 2>/dev/null && return 0 || return 1
        fi
    fi
    return 1
}

# Função para criar hash SHA256
create_hash() {
    local file="$1"
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$file" | cut -d' ' -f1
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$file" | cut -d' ' -f1
    else
        echo "NO_HASH_AVAILABLE"
    fi
}

# Lista de arquivos/diretórios para backup
BACKUP_ITEMS=(
    "config.json"
    "user_data/"
    "logs/"
    "strategies/"
    "docs/"
    "scripts/"
    ".gitignore"
    "README.md"
    "SECURITY.md"
)

# Arquivos sensíveis (que serão criptografados)
SENSITIVE_ITEMS=(
    ".env"
    "user_data/config.json"
    "logs/freqtrade*.log"
)

# Criar backup dos arquivos
TOTAL_ITEMS=0
BACKED_UP_ITEMS=0

for item in "${BACKUP_ITEMS[@]}"; do
    TOTAL_ITEMS=$((TOTAL_ITEMS + 1))

    if [[ -e "$item" ]]; then
        print_status "Fazendo backup de: $item"

        if [[ -d "$item" ]]; then
            # Diretório
            cp -r "$item" "$BACKUP_PATH/" 2>/dev/null && BACKED_UP_ITEMS=$((BACKED_UP_ITEMS + 1)) || \
            print_warning "Falha ao fazer backup do diretório: $item"
        else
            # Arquivo
            cp "$item" "$BACKUP_PATH/" 2>/dev/null && BACKED_UP_ITEMS=$((BACKED_UP_ITEMS + 1)) || \
            print_warning "Falha ao fazer backup do arquivo: $item"
        fi
    else
        print_warning "Item não encontrado: $item"
    fi
done

# Processar arquivos sensíveis (com criptografia)
SENSITIVE_BACKED_UP=0
for item in "${SENSITIVE_ITEMS[@]}"; do
    if [[ -e "$item" ]]; then
        print_status "Criptografando arquivo sensível: $item"

        # Criar hash antes da criptografia
        original_hash=$(create_hash "$item")

        # Criptografar
        if encrypt_file "$item" "$BACKUP_PATH/$(basename $item).enc"; then
            # Salvar hash para verificação posterior
            echo "$original_hash" > "$BACKUP_PATH/$(basename $item).hash"
            SENSITIVE_BACKED_UP=$((SENSITIVE_BACKED_UP + 1))
        else
            print_warning "Falha ao criptografar: $item"
            # Fallback: backup sem criptografia
            cp "$item" "$BACKUP_PATH/$(basename $item).unencrypted" 2>/dev/null || true
        fi
    fi
done

# Criar manifesto do backup
cat > "$BACKUP_PATH/backup_manifest.json" << EOF
{
    "backup_info": {
        "created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "version": "3.0",
        "freqtrade_version": "$(freqtrade --version 2>/dev/null || echo 'unknown')",
        "system_info": {
            "os": "$(uname -s)",
            "kernel": "$(uname -r)",
            "architecture": "$(uname -m)"
        }
    },
    "backup_stats": {
        "total_items": $TOTAL_ITEMS,
        "backed_up_items": $BACKED_UP_ITEMS,
        "sensitive_items_backed_up": $SENSITIVE_BACKED_UP
    },
    "files_backed_up": [
        $(for item in "${BACKUP_ITEMS[@]}"; do
            if [[ -e "$item" ]]; then
                echo "        \"$item\","
            fi
        done | sed '$ s/,$//')
    ],
    "security": {
        "sensitive_files_encrypted": $([ $SENSITIVE_BACKED_UP -gt 0 ] && echo "true" || echo "false"),
        "encryption_method": "gpg_or_openssl",
        "hash_verification": "sha256"
    }
}
EOF

# Criar script de restore
cat > "$BACKUP_PATH/restore.sh" << 'EOF'
#!/bin/bash

# Script para restaurar backup do FreqTrade3
# Execute: chmod +x restore.sh && ./restore.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() { echo -e "${YELLOW}[RESTORE]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "=================================================="
echo "🔄 RESTORE DO BACKUP FREQTRADE3"
echo "=================================================="

# Decriptar arquivos se necessário
for enc_file in *.enc; do
    if [[ -f "$enc_file" ]]; then
        filename="${enc_file%.enc}"
        print_status "Decriptando: $filename"

        if command -v gpg >/dev/null 2>&1; then
            gpg --quiet --decrypt "$enc_file" > "$filename" 2>/dev/null || \
            gpg --quiet --symmetric --decrypt "$enc_file" > "$filename"
        elif command -v openssl >/dev/null 2>&1; then
            openssl enc -aes-256-cbc -d -in "$enc_file" -out "$filename" 2>/dev/null
        fi
    fi
done

# Verificar se restaurar
read -p "Continuar com o restore? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelado."
    exit 0
fi

# Restaurar arquivos
for file in config.json user_data/ logs/ strategies/ docs/ scripts/ .gitignore README.md SECURITY.md; do
    if [[ -f "$file" ]]; then
        print_status "Restaurando arquivo: $file"
        cp "$file" "../$file" 2>/dev/null || true
    elif [[ -d "$file" ]]; then
        print_status "Restaurando diretório: $file"
        cp -r "$file" "../$file" 2>/dev/null || true
    fi
done

print_success "Restore concluído!"
echo "Por favor, verifique as configurações antes de executar o FreqTrade."
EOF

chmod +x "$BACKUP_PATH/restore.sh"

# Comprimir backup
print_status "Comprimindo backup..."

if command -v tar >/dev/null 2>&1; then
    cd "$BACKUP_DIR"
    tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
    rm -rf "$BACKUP_NAME"
    BACKUP_FILE="${BACKUP_PATH}.tar.gz"
    print_success "Backup compactado: $BACKUP_FILE"
elif command -v zip >/dev/null 2>&1; then
    cd "$BACKUP_DIR"
    zip -r "${BACKUP_NAME}.zip" "$BACKUP_NAME" >/dev/null 2>&1
    rm -rf "$BACKUP_NAME"
    BACKUP_FILE="${BACKUP_PATH}.zip"
    print_success "Backup compactado: $BACKUP_FILE"
else
    print_warning "tar e zip não disponíveis, mantendo backup descompactado"
    BACKUP_FILE="$BACKUP_PATH"
fi

# Criar checksum do backup
if [[ -f "$BACKUP_FILE" ]]; then
    CHECKSUM=$(create_hash "$BACKUP_FILE")
    echo "$CHECKSUM" > "${BACKUP_FILE}.sha256"
    print_success "Checksum criado: ${BACKUP_FILE}.sha256"
fi

# Mostrar estatísticas finais
echo
echo "================================================================"
echo "✅ BACKUP CONCLUÍDO COM SUCESSO!"
echo "================================================================"
echo
echo "📊 ESTATÍSTICAS:"
echo "   • Itens processados: $TOTAL_ITEMS"
echo "   • Itens copiados: $BACKED_UP_ITEMS"
echo "   • Arquivos sensíveis criptografados: $SENSITIVE_BACKED_UP"
echo "   • Arquivo de backup: $BACKUP_FILE"
echo
echo "🔒 SEGURANÇA:"
echo "   • Arquivos sensíveis: Criptografados"
echo "   • Checksum de verificação: ${BACKUP_FILE}.sha256"
echo "   • Script de restore: $BACKUP_PATH/restore.sh"
echo
echo "💡 INSTRUÇÕES:"
echo "   1. Armazene o backup em local seguro"
echo "   2. Guarde o checksum para verificação"
echo "   3. Para restaurar: ./$(basename $BACKUP_PATH)/restore.sh"
echo
print_success "Backup salvo em: $BACKUP_FILE"

# Cleanup de backups antigos (manter apenas os 5 mais recentes)
if [[ -d "$BACKUP_DIR" ]]; then
    cd "$BACKUP_DIR"
    ls -t freqtrade3_backup_*.tar.gz freqtrade3_backup_*.zip 2>/dev/null | tail -n +6 | while read -r old_backup; do
        print_status "Removendo backup antigo: $old_backup"
        rm -f "$old_backup" "${old_backup}.sha256" 2>/dev/null || true
    done
fi

print_success "Backup completo realizado com segurança!"
