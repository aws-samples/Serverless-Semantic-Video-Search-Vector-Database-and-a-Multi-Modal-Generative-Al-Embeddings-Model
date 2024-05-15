import { useState } from 'react'
import { get } from 'aws-amplify/api';
import Box from "@cloudscape-design/components/box"
import Container from "@cloudscape-design/components/container"
import SpaceBetween from "@cloudscape-design/components/space-between"
import Alert from "@cloudscape-design/components/alert";
import Header from "@cloudscape-design/components/header"
import Form from "@cloudscape-design/components/form"
import Button from "@cloudscape-design/components/button"
import Spinner from "@cloudscape-design/components/spinner"
import ReactHlsPlayer from 'react-hls-player';

function LivePage() {

    const [liveStreamURL, setLiveStreamURL] = useState(null);
    const [alertText, setAlertText] = useState("");
    const [alertType, setAlertType] = useState("");
    const [alertVisible, setAlertVisible] = useState(false)
    const [isConnecting, setIsConnecting] = useState(false)
    const [autoPlay, setAutoPlay] = useState(false)

    const GetLiveSession = async () => {

        try {
            setIsConnecting(true)
            setAlertText("Connecting to the live camera feed...")
            setAlertType("success")
            setAlertVisible(true)

            const restOperation = get({
                apiName: 'clipcrunchapi',
                path: '/images/liveURL'
            });

            const { body } = await restOperation.response;
            const response = await body.json();

            console.log('API Response:', response)

            setAlertText("")
            setAlertType("")
            setAlertVisible(false)
            setIsConnecting(false)

            setLiveStreamURL(response.sessionURL)
            setAutoPlay(true)

        } catch (error) {
            setAlertText("Live streaming is not available. Please turn on the camera.")
            setAlertType("error")
            setAlertVisible(true)
            setIsConnecting(false)

            setLiveStreamURL(null)
            setAutoPlay(false)

            console.log('GET call failed: ', error);
        }
    }

    return (
        <Box margin={{ bottom: "l", top: "s" }} padding="xxs">
            <Form header={<Header variant="h1">Live Feed</Header>}>

                <Container>
                    <SpaceBetween size='m'>
                        {
                            alertVisible ?
                                <SpaceBetween size='m'>
                                    <Alert
                                        type={alertType}
                                        header={alertText} onDismiss={() => { setAlertVisible(false) }}
                                    /></SpaceBetween> : <></>
                        }

                        {
                            liveStreamURL ?
                                <>
                                    <Box textAlign='center'>
                                        <ReactHlsPlayer
                                            src={liveStreamURL}
                                            autoPlay={autoPlay}
                                            controls={true}
                                            width="auto"
                                            height="auto"
                                        />
                                    </Box>
                                    <Box textAlign='center'>
                                        <Button variant='primary' onClick={()=> setLiveStreamURL(null)}>Disconnect</Button>
                                    </Box>
                                </>
                                :
                                <Button disabled={isConnecting} variant='primary'
                                    onClick={
                                        async () => GetLiveSession()
                                    }>{isConnecting ? <Spinner /> : "Connect"}
                                </Button>
                        }
                    </SpaceBetween>
                </Container>
            </Form>
        </Box>
    )
}

export default LivePage;
