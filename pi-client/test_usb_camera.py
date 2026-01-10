"""Test USB webcam (Camera 1)"""
import cv2

print("Opening USB webcam (Camera 1)...")
cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("ERROR: USB webcam not found!")
    exit(1)

print("USB Webcam preview - press 'q' to quit")
cv2.namedWindow("USB Webcam", cv2.WINDOW_NORMAL)

while True:
    ret, frame = cap.read()
    if ret:
        cv2.imshow("USB Webcam", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("Done!")
