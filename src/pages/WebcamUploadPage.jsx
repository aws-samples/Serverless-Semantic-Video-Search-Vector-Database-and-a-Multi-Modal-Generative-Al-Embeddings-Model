import { useCallback, useRef, useState, useEffect } from 'react'
import { get } from 'aws-amplify/api';
import Box from "@cloudscape-design/components/box"
import Container from "@cloudscape-design/components/container"
import SpaceBetween from "@cloudscape-design/components/space-between"
import Alert from "@cloudscape-design/components/alert";
import Header from "@cloudscape-design/components/header"
import Form from "@cloudscape-design/components/form"
import Button from "@cloudscape-design/components/button"
import Spinner from "@cloudscape-design/components/spinner"
import Toggle from "@cloudscape-design/components/toggle";
import Select from "@cloudscape-design/components/select";
import Webcam from "react-webcam";
import { uploadData } from 'aws-amplify/storage';
import { Buffer } from "buffer"

function WebcamUploadPage() {

    const webcamRef = useRef(null);
    const mediaRecorderRef = useRef(null);
    const [imgSrc, setImgSrc] = useState(null);
    const [mirrored, setMirrored] = useState(false);

    const [alertText, setAlertText] = useState("");
    const [alertType, setAlertType] = useState("");
    const [alertVisible, setAlertVisible] = useState(false)
    const [isUploading, setIsUploading] = useState(false)
    const [capturing, setCapturing] = useState(false);
    const [recordedChunks, setRecordedChunks] = useState([]);
    const [devices, setDevices] = useState([]);
    const [selectedDevice, setSelectedDevice] = useState(null);

    const handleDevices = useCallback(
        (mediaDevices) =>
            setDevices(mediaDevices.filter(({ kind }) => kind === "videoinput")),
        [setDevices]
    );

    useEffect(() => {
        navigator.mediaDevices.enumerateDevices().then(handleDevices);
    }, [handleDevices]);

    useEffect(() => {
        if (devices.length > 0 && !selectedDevice) {
            setSelectedDevice(devices[0]);
        }
    }, [devices, selectedDevice]);

    // create a capture function
    const captureImage = useCallback(() => {
        setAlertVisible(false)
        const imageSrc = webcamRef.current.getScreenshot();
        setImgSrc(imageSrc);
    }, [webcamRef]);

    const retakeImage = () => {
        setAlertVisible(false)
        setImgSrc(null);
    };

    const uploadPhoto = async () => {
        setIsUploading(true)

        const filename = "webcamUploads/" + Date.now() + ".jpg";

        var buf = Buffer.from(imgSrc.replace(/^data:image\/\w+;base64,/, ""),'base64')

        try {
            const result = await uploadData({
                key: filename,
                data: buf,
                options:  {
                    contentType: "image/jpeg"
                }
            }).result;
            console.log('Succeeded: ', result);

            setAlertText(`Successfully uploaded webcam image as ${filename}`)
            setAlertType("success")
            setAlertVisible(true)
        } catch (error) {
            console.log(imgSrc)
            console.log('Error : ', error);
            setAlertText("Webcam image failed to upload. Check console log for more information")
            setAlertType("error")
            setAlertVisible(true)
        }

        setIsUploading(false)
        setImgSrc(null);
    };

    const handleDataAvailable = useCallback(
        ({ data }) => {
            if (data.size > 0) {
                setRecordedChunks((prev) => prev.concat(data));
            }
        },
        [setRecordedChunks]
    );

    const handleStartCaptureClick = useCallback(() => {
        setCapturing(true)
        setRecordedChunks([])
        mediaRecorderRef.current = new MediaRecorder(webcamRef.current.stream, {
            mimeType: "video/webm",
        });
        mediaRecorderRef.current.addEventListener(
            "dataavailable",
            handleDataAvailable
        );
        mediaRecorderRef.current.start();
    }, [webcamRef, setCapturing, mediaRecorderRef, handleDataAvailable]);

    const handleStopCaptureClick = useCallback(() => {
        mediaRecorderRef.current.stop();
        setCapturing(false);
    }, [mediaRecorderRef, setCapturing]);
    const uploadVideo = async () => {
        setIsUploading(true)

        const filename = "webcamUploads/" + Date.now() + ".webm";

        if (recordedChunks.length) {
            const blob = new Blob(recordedChunks, {
                type: "video/webm",
            });

            try {
                const result = await uploadData({
                    key: filename,
                    data: blob,
                }).result;
                console.log('Succeeded: ', result);

                setAlertText(`Successfully uploaded webcam video as ${filename}`)
                setAlertType("success")
                setAlertVisible(true)
            } catch (error) {
                console.log(imgSrc)
                console.log('Error : ', error);
                setAlertText("Webcam video failed to upload. Check console log for more information")
                setAlertType("error")
                setAlertVisible(true)
            }
        }
        setIsUploading(false)
        setRecordedChunks([])
    };

    const handleDeviceChange = (event) => {
        setSelectedDevice(event.detail.selectedOption);
    };

    return (
        <Box margin={{ bottom: "l", top: "s" }} padding="xxs">
            <Form header={<Header variant="h1">Webcam Upload</Header>}>
                <Container>
                    <SpaceBetween size='m'>
                        {alertVisible && (
                            <SpaceBetween size='m'>
                                <Alert
                                    type={alertType}
                                    header={alertText}
                                    onDismiss={() => { setAlertVisible(false) }}
                                />
                            </SpaceBetween>
                        )}

                        <Toggle
                            onChange={({ detail }) => setMirrored(detail.checked)}
                            checked={mirrored}
                        >
                            Mirrored
                        </Toggle>

                        <Select
                            selectedOption={selectedDevice}
                            onChange={handleDeviceChange}
                            options={devices.map((device, index) => ({
                                label: device.label || `Camera ${index + 1}`,
                                value: device.deviceId
                            }))}
                            placeholder="Select a camera"
                            disabled={isUploading || capturing || imgSrc !== null}
                        />

                        {imgSrc ? (
                            <img src={imgSrc} alt="webcam" />
                        ) : (
                            <Webcam
                                height={600}
                                width={600}
                                ref={webcamRef}
                                mirrored={mirrored}
                                screenshotFormat="image/jpeg"
                                videoConstraints={selectedDevice ? { deviceId: selectedDevice.value } : undefined}
                            />
                        )}

                        {recordedChunks.length === 0 && !capturing && (imgSrc ? (
                            <Button variant='primary'
                                    disabled={isUploading}
                                    onClick={retakeImage}>
                                Retake Image
                            </Button>
                        ) : (
                            <Button variant='primary'
                                    disabled={isUploading}
                                    onClick={captureImage}>
                                Capture Image
                            </Button>
                        ))}

                        {!imgSrc && (capturing ? (
                            <Button variant='primary'
                                    disabled={isUploading}
                                    onClick={handleStopCaptureClick}>
                                Stop Video Capture
                            </Button>
                        ) : (
                            <Button variant='primary'
                                    disabled={isUploading}
                                    onClick={handleStartCaptureClick}>
                                Start Video Capture
                            </Button>
                        ))}

                        {recordedChunks.length !== 0 &&
                            <Button variant='primary'
                                    disabled={isUploading}
                                    onClick={uploadVideo}>
                                {isUploading ? <Spinner /> : "Upload Video"}
                            </Button>
                        }

                        {imgSrc &&
                            <Button disabled={isUploading}
                                    onClick={uploadPhoto}>{isUploading ? <Spinner /> : "Upload Image"}
                            </Button>
                        }
                    </SpaceBetween>
                </Container>
            </Form>
        </Box>
    )
}

export default WebcamUploadPage;
