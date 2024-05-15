import '@aws-amplify/ui-react/styles.css';

import { useState, useEffect } from 'react'
import { Amplify } from 'aws-amplify';
import { Hub } from 'aws-amplify/utils';
import { getCurrentUser } from 'aws-amplify/auth';
import AppLayout from "@cloudscape-design/components/app-layout"

import NavBar from './components/NavBar';
import ToolsBar from './components/ToolsBar';
import SideBar from './components/SideBar';
import Routes from './Routes';

import amplifyConfig from "./aws-exports";

import { Authenticator } from '@aws-amplify/ui-react';

function App() {

  if (window.location.hostname.includes("localhost")) {
    amplifyConfig.oauth.redirectSignIn = "http://localhost:5173/";
    amplifyConfig.oauth.redirectSignOut = "http://localhost:5173/";
  }

  Amplify.configure(amplifyConfig);

  const [user, setUser] = useState(null);



  useEffect(() => {
    Hub.listen('auth', ({ payload: { event, data } }) => {
      console.log(event, data);
      switch (event) {
        case 'signIn':
          console.log(event)
          console.log(data)
          getUser().then(userData => setUser(userData));
          break;
        case 'signOut':
          setUser(null);
          console.log('Sign out');
          break;
        case 'signedOut':
          location.reload();
          break;
        case 'signedIn':
          location.reload();
          break;
        case 'signIn_failure':
          console.log('Sign in failure', data);
          break;
      }
    });

    getUser().then(userData => setUser(userData));
  }, []);

  function getUser() {
    return getCurrentUser()
      .then(userData => userData)
      .catch(() => console.log('Not signed in'));
  }


  return (
    <>
      <NavBar title={"Amazon Web Services"} isAuthenticated={user ? true : false} user={user} />
      <AppLayout
        navigation={<SideBar title={"Clip Crunch"} items={[
          { type: "link", text: "Search", href: "/" },
          ... __KINESIS_VIDEO_STREAM_INTEGRATION__ ? [{ type: "link", text: "Live", href: "/live" }] : [],
          { type: "link", text: "Webcam Upload", href: "/webcamupload" },
          { type: "link", text: "File Upload", href: "/fileupload" }
        ]} />}
        tools={<ToolsBar title={"Help"} text={"Use this app to search video feeds"} />}
        content={user ? <Routes /> : <Authenticator />}
      />
    </>
  )
}

export default App