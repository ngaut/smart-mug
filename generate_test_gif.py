from PIL import Image, ImageDraw

# Settings
width = 96
height = 24
frames = []
num_frames = 8
block_size = 12

# Generate frames
for i in range(num_frames):
    # Create new black image
    img = Image.new('1', (width, height), 0) # '1' for 1-bit pixels, black background (0)
    draw = ImageDraw.Draw(img)
    
    # Calculate position
    x = (i * (width // num_frames)) % width
    
    # Draw white block
    # In 1-bit mode, 1 is white
    draw.rectangle([x, 4, x + block_size, 20], fill=1)
    
    frames.append(img)

# Save as GIF
frames[0].save(
    'test_animation.gif',
    save_all=True,
    append_images=frames[1:],
    duration=500, # 500ms per frame
    loop=0
)

print("Generated test_animation.gif")
