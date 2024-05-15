import { useState } from 'react'
import { post, get } from 'aws-amplify/api';
import { getUrl } from 'aws-amplify/storage'
import Header from "@cloudscape-design/components/header"
import Form from "@cloudscape-design/components/form"
import FormField from "@cloudscape-design/components/form-field"
import Input from "@cloudscape-design/components/input"
import Box from "@cloudscape-design/components/box"
import Container from "@cloudscape-design/components/container"
import SpaceBetween from "@cloudscape-design/components/space-between"
import Spinner from "@cloudscape-design/components/spinner"
import Alert from "@cloudscape-design/components/alert";
import Grid from "@cloudscape-design/components/grid";
import Select from "@cloudscape-design/components/select";
import Modal from "@cloudscape-design/components/modal";
import Toggle from "@cloudscape-design/components/toggle";
import ReactHlsPlayer from 'react-hls-player';

import "./SearchPage.css"

function MainPage() {

    const [showModal, setShowModal] = useState(false)

    const [searchString, setSearchString] = useState("");
    const [days, setDays] = useState({ label: "365", value: "365" });
    const [confidenceThreshold, setConfidenceThreshold] = useState(42);
    const [includeSimilarTimestamp, setIncludeSimilarTimestamp] = useState(true)

    const [streamURL, setStreamURL] = useState("");

    const [isProcessing, setIsProcessing] = useState(false)
    const [alertText, setAlertText] = useState("");
    const [alertType, setAlertType] = useState("");
    const [alertVisible, setAlertVisible] = useState(false)
    const [images, setImages] = useState([]);

    const setError = (message) => {
        setAlertText(message)
        setAlertType("error")
        setAlertVisible(true)
    }

    const setSuccess = (message) => {
        setAlertText(message)
        setAlertType("success")
        setAlertVisible(true)
    }

    const getVideoClipURL = async (timestamp) => {

        try {
            const restOperation = get({
                apiName: 'clipcrunchapi',
                path: '/images/sessionURL',
                options: {
                    queryParams: {
                        timestamp: timestamp
                    }
                }
            });

            const { body } = await restOperation.response;
            const response = await body.json();

            console.log('API Response:', response)

            return response.sessionURL

        } catch (error) {
            setIsProcessing(false)
            setError("An error occurred processing the search")
            console.log('GET call failed: ', error);
        }
    }

    const searchImages = async () => {

        setImages([])

        try {
            if (searchString.trim()) {
                setIsProcessing(true)
                const item = {
                    searchString: searchString,
                    days: days.value,
                    confidenceThreshold: confidenceThreshold,
                    includeSimilarTimestamp: includeSimilarTimestamp
                };

                const restOperation = post({
                    apiName: 'clipcrunchapi',
                    path: '/images/search',
                    options: {
                        body: item
                    }
                });

                const { body } = await restOperation.response;
                const response = await body.json();

                console.log('API Response:', response)

                let newImages = []
                for (let image of response.images) {
                    const imageResponse = await getUrl({ key: image.file });
                    image.url = imageResponse.url
                    newImages.push(image)
                    console.log(image)
                }

                setImages(newImages)
                setIsProcessing(false)

                if (newImages.length === 0) {
                    setError("No images found")
                } else {
                    setSuccess("Search completed. Found " + newImages.length + " images")
                }
            }

        } catch (error) {
            setIsProcessing(false)
            setError("An error occurred processing the search")
            console.log('POST call failed: ', error);
        }
    }

    return (
        <Box margin={{ bottom: "l", top: "s" }} padding="xxs">
            <Form
                errorText=""
                header={<Header variant="h1">Search Videos</Header>}
            >
                <SpaceBetween size='m'>
                    <Container>
                        <SpaceBetween size='l'>
                            {
                                alertVisible ?
                                    <Alert
                                        dismissible
                                        type={alertType}
                                        header={alertText} onDismiss={() => { setAlertVisible(false) }}
                                    /> : <></>
                            }

                            <FormField>
                                <Input value={searchString} type="search" inputMode="search" placeholder="Search Videos" autoFocus={true}
                                    onChange={({ detail }) => {
                                        setSearchString(detail.value)

                                        if (detail.value.length === 0) {
                                            setImages([])
                                        }
                                    }}
                                    onKeyDown={({ detail }) => {
                                        if (detail.keyCode == 13) {
                                            searchImages()
                                        }
                                    }}
                                />
                            </FormField>
                            <FormField description={"Days"}>
                                <Select
                                    selectedOption={days}
                                    onChange={({ detail }) => {
                                        setDays(detail.selectedOption)
                                    }
                                    }
                                    options={[
                                        { label: "1", value: "1" },
                                        { label: "2", value: "2" },
                                        { label: "7", value: "7" },
                                        { label: "30", value: "30" },
                                        { label: "365", value: "365" }
                                    ]}
                                />

                            </FormField>
                            <FormField description={"Confidence"}>
                                <Input
                                    onChange={({ detail }) => {
                                        setConfidenceThreshold(detail.value)
                                    }
                                    }
                                    onKeyDown={({ detail }) => {
                                        if (detail.keyCode == 13) {
                                            searchImages()
                                        }
                                    }}
                                    value={confidenceThreshold}
                                    inputMode="numeric"
                                    type="number"
                                />
                            </FormField>
                            <Toggle
                                onChange={({ detail }) =>
                                    setIncludeSimilarTimestamp(detail.checked)
                                }
                                checked={includeSimilarTimestamp}
                            >
                                Include images with similar timestamp
                            </Toggle>
                        </SpaceBetween>
                    </Container>

                    {isProcessing ? <Box textAlign="center"><Spinner size='large' /></Box> :
                        images.length > 0 ?
                            <>
                                <Grid
                                    gridDefinition={images.map(() => (
                                        { colspan: { default: 6, m: 6, l: 4 } }
                                    ))}
                                >
                                    {
                                        images.map(image => (
                                            <Container key={Math.random()}>
                                                <div key={Math.random()}>
                                                    <img
                                                        src={image.url}
                                                        key={Math.random()}
                                                        style={{ width: "100%", height: "100%" }}
                                                        onClick={async () => {
                                                            if(__KINESIS_VIDEO_STREAM_INTEGRATION__) {
                                                                const u = await getVideoClipURL(image.timestamp)
                                                                if (u) {
                                                                    setStreamURL(u)
                                                                    setShowModal(true)
                                                                }
                                                            }
                                                        }
                                                        }
                                                    />
                                                    <p><strong>Timestamp:</strong> {new Date(image.timestamp).toLocaleString()}</p>
                                                    <p><strong>Confidence:</strong> {image.confidence.toFixed(2)}</p>
                                                </div>
                                            </Container>
                                        ))
                                    }
                                </Grid>
                            </>
                            : <></>
                    }

                </SpaceBetween>

            </Form>
            <Modal
                onDismiss={() => {
                    setShowModal(false)
                    setStreamURL("")
                }}
                visible={showModal}
                header="Video Clip"
                size='large'
            >
                <Box textAlign='center'>
                    <ReactHlsPlayer
                        src={streamURL}
                        autoPlay={true}
                        controls={true}
                        width="100%"
                        height="auto"
                    />
                </Box>
            </Modal>
        </Box>
    )
}

export default MainPage;
