import pygame
import serial
import math
import csv
import time

# --- Configuration ---
COM_PORT = 'COM3'  # Update to your ESP32's COM port
BAUD_RATE = 115200
FPS = 60

# Task conditions (3 widths x 3 distances)[cite: 4]
WIDTHS = [40, 80, 120]
DISTANCES = [200, 400, 600]

pygame.init()
screen = pygame.display.set_mode((1280, 720))
pygame.display.set_caption("Fitts' Law ESP32 UI")
clock = pygame.time.Clock()

try:
    esp_serial = serial.Serial(COM_PORT, BAUD_RATE, timeout=0.01)
except Exception as e:
    print(f"Failed to connect to {COM_PORT}: {e}")
    exit()

def calculate_id(d, w):
    """The Index of Difficulty is ID = log2(D/W + 1)[cite: 2]."""
    return math.log2((d / w) + 1)

def check_overlap(obj_rect, target_rect):
    """Check if the released object overlaps the target by more than 80% of the object's area[cite: 3]."""
    clip = obj_rect.clip(target_rect)
    overlap_area = clip.width * clip.height
    object_area = obj_rect.width * obj_rect.height
    return (overlap_area / object_area) >= 0.80 if object_area > 0 else False

# State variables
cursor_x, cursor_y, is_pinched = 0, 0, False
object_engaged = False
start_time = 0
current_trial = 0
trials_data = []
participant_id = "P01"

# Initialize first condition
current_w = WIDTHS[0]
current_d = DISTANCES[0]
target_rect = pygame.Rect(800, 360 - 100, current_w, 200) # Centers at same height[cite: 3]
object_rect = pygame.Rect(800 - current_d, 360 - 100, current_w, 200) # Same size as target[cite: 3]

running = True
while running:
    screen.fill((255, 255, 255))
    
    # Process Windows events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Read ESP32 Serial Stream[cite: 3]
    if esp_serial.in_waiting:
        line = esp_serial.readline().decode('utf-8', errors='ignore').strip()
        if line:
            try:
                cx, cy, btn = map(int, line.split(','))
                cursor_x, cursor_y = cx, cy
                new_pinch = bool(btn)
                
                # Check for engagement (pinch down over object)[cite: 3]
                if new_pinch and not is_pinched and object_rect.collidepoint(cursor_x, cursor_y):
                    object_engaged = True
                    start_time = time.time()
                
                # Check for release (pinch up while engaged)[cite: 3]
                elif not new_pinch and is_pinched and object_engaged:
                    object_engaged = False
                    mt = (time.time() - start_time) * 1000 # Movement Time in ms[cite: 2]
                    
                    success = check_overlap(object_rect, target_rect)
                    id_val = calculate_id(current_d, current_w)
                    
                    # Log trial[cite: 3, 4]
                    trials_data.append([
                        participant_id, current_trial, current_d, current_w, 
                        round(id_val, 3), round(mt, 2), "Success" if success else "Failure"
                    ])
                    
                    # Provide success/failure feedback[cite: 3]
                    print(f"Trial {current_trial}: {'Success' if success else 'Failure'} | MT: {mt:.2f}ms | ID: {id_val:.2f}")
                    
                    if success:
                        current_trial += 1
                        # TODO: Cycle through the 9 conditions (3 widths x 3 distances) randomly or counterbalanced[cite: 4].
                    
                    # Reset object position for the next attempt or trial
                    object_rect.x = target_rect.x - current_d
                    
                is_pinched = new_pinch
            except ValueError:
                pass # Ignore malformed serial lines

    # Update engaged object position
    if object_engaged:
        # Move object along 1D X-axis, keeping height constant[cite: 3]
        object_rect.centerx = cursor_x

    # Draw Target, Object, and Cursor[cite: 3]
    pygame.draw.rect(screen, (200, 200, 200), target_rect, 2) # Target (Outline)
    pygame.draw.rect(screen, (100, 150, 255) if object_engaged else (150, 150, 150), object_rect) # Object
    pygame.draw.circle(screen, (255, 0, 0), (cursor_x, cursor_y), 10) # Cursor

    pygame.display.flip()
    clock.tick(FPS)

# Export Logs on close[cite: 4]
with open('fitts_law_results.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Participant_ID", "Trial", "D", "W", "ID", "MT_ms", "Outcome"])
    writer.writerows(trials_data)

pygame.quit()
esp_serial.close()