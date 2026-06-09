#!/bin/bash
# Watermark v12 — clean chessboard, "Naumova.by" only
set -e

SITE_ROOT="/var/www/site-ofskin/webroot"

process_photo() {
    local photo="$1"
    local count="$2"
    local total="$3"
    
    COMMENT=$(identify -format "%c" "$photo" 2>/dev/null)
    if [ "$COMMENT" = "watermarked-v12" ]; then
        echo "[$count/$total] SKIP: ${photo#$SITE_ROOT/}"
        return
    fi
    
    local DIMS=$(identify -format "%wx%h" "$photo" 2>/dev/null)
    
    convert "$photo" \
      -resize '1600x1600>' \
      -fill 'rgba(255,255,255,0.20)' \
      -font 'Helvetica-Bold' -pointsize 80 \
      -annotate -25x0+20+80 'Naumova.by' \
      -annotate -25x0+380+130 'Naumova.by' \
      -annotate -25x0+740+180 'Naumova.by' \
      -annotate -25x0+1100+230 'Naumova.by' \
      -annotate -25x0+1460+280 'Naumova.by' \
      -annotate -25x0+200+500 'Naumova.by' \
      -annotate -25x0+560+550 'Naumova.by' \
      -annotate -25x0+920+600 'Naumova.by' \
      -annotate -25x0+1280+650 'Naumova.by' \
      -annotate -25x0+20+920 'Naumova.by' \
      -annotate -25x0+380+970 'Naumova.by' \
      -annotate -25x0+740+1020 'Naumova.by' \
      -annotate -25x0+1100+1070 'Naumova.by' \
      -annotate -25x0+1460+1120 'Naumova.by' \
      -annotate -25x0+200+1340 'Naumova.by' \
      -annotate -25x0+560+1390 'Naumova.by' \
      -annotate -25x0+920+1440 'Naumova.by' \
      -annotate -25x0+1280+1490 'Naumova.by' \
      -quality 92 -set comment 'watermarked-v12' \
      "$photo" 2>/dev/null
    
    local NEW_DIMS=$(identify -format "%wx%h" "$photo" 2>/dev/null)
    echo "[$count/$total] OK: ${photo#$SITE_ROOT/} (${DIMS} -> ${NEW_DIMS})"
}

echo "=== Watermark v12 — Helvetica-Bold 80pt, 4 rows, chessboard ==="

find "$SITE_ROOT" \( -path "*/albums/*" -o -path "*/photos/*" -o -path "*/instagram_content/photos/*" -o -path "*/wfolio-assets/*" \) \( -iname "*.jpg" -o -iname "*.jpeg" \) -type f > /tmp/photo_list.txt
TOTAL=$(wc -l < /tmp/photo_list.txt)
echo "Found $TOTAL images"

COUNT=0
while IFS= read -r photo; do
    COUNT=$((COUNT + 1))
    process_photo "$photo" "$COUNT" "$TOTAL"
done < /tmp/photo_list.txt

echo ""
echo "=== All $TOTAL photos watermarked (v12) ==="