#!/bin/zsh
# Quét CHỈ ĐỌC dung lượng Mac. Không xoá, không sửa gì.
# Dùng: zsh scan.sh <thư-mục-output>
OUT=${1:-/tmp/mac-cleanup-scan}; mkdir -p "$OUT"
sec(){ print "\n===== $1 ====="; }
{
sec "Ổ đĩa"; df -h /System/Volumes/Data | tail -1; sysctl vm.swapusage; tmutil listlocalsnapshots / 2>/dev/null | tail -5
sec "Home (cấp 1)"; du -xhd1 ~ 2>/dev/null | sort -rh | head -30
sec "Library"; du -xhd1 ~/Library 2>/dev/null | sort -rh | head -15
sec "Library/Caches"; du -xhd1 ~/Library/Caches 2>/dev/null | sort -rh | head -25
sec "Application Support"; du -xhd1 ~/Library/Application\ Support 2>/dev/null | sort -rh | head -20
sec "Containers"; du -xhd1 ~/Library/Containers 2>/dev/null | sort -rh | head -10
sec "Cache dev"; du -sh ~/.npm/_cacache ~/.npm/_npx ~/Library/pnpm/store ~/.cache/* ~/.local/share/uv ~/go/pkg/mod ~/Library/Developer ~/.gradle ~/.cargo/registry ~/Library/Caches/ms-playwright 2>/dev/null | sort -rh
sec "HuggingFace"; du -sh ~/.cache/huggingface/hub/* 2>/dev/null | sort -rh | head -15
sec "Node (nvm)"; du -sh ~/.nvm/versions/node/* 2>/dev/null; print -n "default: "; cat ~/.nvm/alias/default 2>/dev/null; print
sec "Claude Desktop"; du -sh ~/Library/Application\ Support/Claude/* 2>/dev/null | sort -rh | head -8
sec "Thùng rác"; du -sh ~/.Trash 2>/dev/null; ls -A ~/.Trash 2>/dev/null | wc -l
sec "Downloads"; du -xhd1 ~/Downloads 2>/dev/null | sort -rh | head -15
sec "Docker"
if command -v docker >/dev/null && docker info >/dev/null 2>&1; then
  docker system df; print "-- container:"; docker ps -a --format '{{.Names}}\t{{.Image}}\t{{.Status}}'
  print "-- volume dangling:"; docker volume ls -qf dangling=true
  print "-- volume theo dung lượng:"; docker system df -v 2>/dev/null | sed -n '/Local Volumes/,/Build cache/p' | sort -k3 -h | tail -25
  du -h ~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw 2>/dev/null
else print "Docker không chạy hoặc không cài"; fi
} > "$OUT/overview.txt" 2>&1

# Thư mục build còn sót trong các dự án (node_modules, .next, dist, .venv…)
cd ~ && find . -xdev \( -path ./Library -o -path ./.Trash -o -path ./.npm -o -path ./.cache -o -path ./.nvm -o -path ./Documents \) -prune -o -type d \( -name node_modules -o -name .next -o -name dist -o -name build -o -name .turbo -o -name target -o -name .venv -o -name venv -o -name __pycache__ -o -name .gradle -o -name Pods -o -name .expo -o -name .parcel-cache -o -name .svelte-kit -o -name .nuxt \) -prune -print 2>/dev/null \
 | grep -v '/node_modules/.*/node_modules' | tr '\n' '\0' | xargs -0 du -sk 2>/dev/null | sort -rn \
 | awk '{printf "%.0fM\t",$1/1024; $1=""; sub(/^ /,""); print}' > "$OUT/build-dirs.tsv"

# File trùng (>1 MB, so md5) trong thư mục người dùng
find Pictures Downloads Desktop Movies -xdev -type f -size +1M -not -path '*/node_modules/*' -not -path '*.photoslibrary/*' -print0 2>/dev/null | xargs -0 stat -f '%z	%N' > "$OUT/files.tsv"
awk -F'\t' 'NR==FNR{c[$1]++; next} c[$1]>1 {print $2}' "$OUT/files.tsv" "$OUT/files.tsv" | tr '\n' '\0' | xargs -0 md5 -r 2>/dev/null \
 | awk '{h=$1; $1=""; sub(/^ /,""); n[h]++; f[h]=f[h] "|" $0} END {for(k in n) if(n[k]>1) print n[k] "\t" f[k]}' > "$OUT/dups.txt"

# Documents có thể bị macOS (TCC) chặn
ls ~/Documents >/dev/null 2>&1 && print ok > "$OUT/documents-access" || print blocked > "$OUT/documents-access"
print "Xong. Kết quả trong $OUT: overview.txt build-dirs.tsv dups.txt documents-access"
