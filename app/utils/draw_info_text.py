import cv2 as cv


def draw_info_text(image, handedness):
    info_text = handedness.classification[0].label[0:]
    cv.putText(
        image,
        info_text,
        cv.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        1,
        cv.LINE_AA,
    )

    return image
