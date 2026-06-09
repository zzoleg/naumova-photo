#!/bin/bash
# Watermark + resize all photos - V11 variant
# Sedan 38pt, 8 rows, alternating text, -18 rotation, 15% opacity

set -e

SEDAN="/var/www/site-ofskin/webroot/fonts/Sedan-Regular.ttf"
SITE_ROOT="/var/www/site-ofskin/webroot"
TILE="/tmp/wm_tile_v11.png"
MAX_DIM=1600
OPACITY=15

echo "=== Creating V11 watermark tile ==="
convert -size 1200x550 xc:none \
  -fill "rgba(255,255,255,0.18)" \
  -font "$SEDAN" -pointsize 38 \
  -gravity West \
  -annotate +0+5 "Alena Naumova   Naumova.by   Alena Naumova   Naumova.by   Alena Naumova" \
  -annotate +0+70 "Naumova.by   Alena Naumova   Naumova.by   Alena Naumova   Naumova.by" \
  -annotate +0+135 "Alena Naumova   Naumova.by   Alena Naumova   Naumova.by   Alena Naumova" \
  -annotate +0+200 "Naumova.by   Alena Naumova   Naumova.by   Alena Naumova   Naumova.by" \
  -annotate +0+265 "Alena Naumova   Naumova.by   Alena Naumova   Naumova.by   Alena Naumova" \
  -annotate +0+330 "Naumova.by   Alena Naumova   Naumova.by   Alena Naumova   Naumova.by" \
  -annotate +0+395 "Alena Naumova   Naumova.by   Alena Naumova   Naumova.by   Alena Naumova" \
  -annotate +0+460 "Naumova.by   Alena Naumova   Naumova.by   Alena Naumova   Naumova.by" \
  -rotate -18 \
  "$TILE"
echo "Tile: $(identify $TILE)"
echo ""

echo "=== Processing all photos ==="

find "$SITE_ROOT" \( -path "*/albums/*" -o -path "*/photos/*" -o -path "*/instagram_content/photos/*" -o -path "*/wfolio-assets/*" \) \( -iname "*.jpg" -o -iname "*.jpeg" \) -type f > /tmp/photo_list.txt
TOTAL=$(wc -l < /tmp/photo_list.txt)
echo "Found $TOTAL images"

COUNT=0
while IFS= read -r photo; do
    COUNT=$((COUNT + 1))
    
    COMMENT=$(identify -format "%c" "$photo" 2>/dev/null)
    if [ "$COMMENT" = "watermarked-v11" ]; then
        echo "[$COUNT/$TOTAL] SKIP: ${photo#$SITE_ROOT/}"
        continue
    fi
    
    DIMS=$(identify -format "%wx%h" "$photo" 2>/dev/null)
    
    convert "$photo" \
      -resize '1600x1600>' \
      \( +clone -tile "$TILE" -draw "color 0,0 reset" \) \
      -compose dissolve -define compose:args=$OPACITY \
      -composite \
      -quality 92 -set comment "watermarked-v11" \
      "$photo" 2>/dev/null
    
    NEW_DIMS=$(identify -format "%wx%h" "$photo" 2>/dev/null)
    echo "[$COUNT/$TOTAL] OK: ${photo#$SITE_ROOT/} (${DIMS} -> ${NEW_DIMS})"
done < /tmp/photo_list.txt

echo ""
echo "=== All $TOTAL photos watermarked (V11) ==="