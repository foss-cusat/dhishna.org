import sharp from 'sharp';
await sharp('public/campus-poster.png').webp({ quality: 86 }).toFile('public/campus-poster.webp');
console.log('Prepared optimized campus poster');
