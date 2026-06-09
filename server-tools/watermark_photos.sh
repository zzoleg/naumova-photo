#!/bin/bash
# Watermark + resize all photos on naumova.ofskinandsouls.com
# Diagonal repeating pattern: "Alena Naumova" / "Naumova.by"

set -e

SITE_ROOT="/var/www/site-ofskin/webroot"

echo "=== Creating watermark tile ==="
convert -size 1200x120 xc:none \
  -fill "rgba(255,255,255,0.15)" \
  -font "Helvetica-Bold" -pointsize 32 \
  -gravity West \
  -annotate +0+0 "Alena Naumova    Alena Naumova    Alena Naumova    Alena Naumova" \
  -annotate +0+62 "Naumova.by       Naumova.by       Naumova.by       Naumova.by" \
  -rotate -28 \
  /tmp/watermark_tile.png
echo "Tile: $(identify /tmp/watermark_tile.png)"
echo ""

echo "=== Processing all photos ==="

find "$SITE_ROOT" \( -path "*/albums/*" -o -path "*/photos/*" -o -path "*/instagram_content/photos/*" -o -path "*/wfolio-assets/*" \) \( -iname "*.jpg" -o -iname "*.jpeg" \) -type f > /tmp/photo_list.txt
TOTAL=$(wc -l < /tmp/photo_list.txt)
echo "Found $TOTAL images"

COUNT=0
while IFS= read -r photo; do
    COUNT=$((COUNT + 1))
    
    COMMENT=$(identify -format "%c" "$photo" 2>/dev/null)
    if [ "$COMMENT" = "watermarked" ]; then
        echo "[$COUNT/$TOTAL] SKIP: ${photo#$SITE_ROOT/}"
        continue
    fi
    
    DIMS=$(identify -format "%wx%h" "$photo" 2>/dev/null)
    
    convert "$photo" \
      -resize '1600x1600>' \
      \( +clone -tile /tmp/watermark_tile.png -draw "color 0,0 reset" \) \
      -compose dissolve -define compose:args=8 \
      -composite \
      -quality 92 -set comment "watermarked" \
      "$photo" 2>/dev/null
    
    NEW_DIMS=$(identify -format "%wx%h" "$photo" 2>/dev/null)
    echo "[$COUNT/$TOTAL] OK: ${photo#$SITE_ROOT/} (${DIMS} -> ${NEW_DIMS})"
done < /tmp/photo_list.txt

echo ""
echo "=== All $TOTAL photos processed ==="