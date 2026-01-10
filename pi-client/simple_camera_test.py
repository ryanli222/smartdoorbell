"""Simple camera test - no imports from doorcam package"""
import cv2
import time

print("=" * 50)
print("Simple Camera Test")
print("=" * 50)

print("\n[1] Opening camera...")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("ERROR: Camera not found!")
    exit(1)

print("[2] Camera opened successfully!")
print(f"    Resolution: {int(cap.get(3))}x{int(cap.get(4))}")

print("[3] Creating preview window...")
cv2.namedWindow("Test Preview", cv2.WINDOW_NORMAL)

print("[4] Starting preview loop (press 'q' to quit)...")
print()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to read frame")
        time.sleep(0.1)
        continue
    
    # Add text overlay
    cv2.putText(frame, "Press 'q' to quit", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    
    cv2.imshow("Test Preview", frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break

print("\n[5] Cleaning up...")
cap.release()
cv2.destroyAllWindows()
print("Done!")
