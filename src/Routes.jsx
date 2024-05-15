import {
    createBrowserRouter,
    RouterProvider,
} from "react-router-dom";

import SearchPage from "./pages/SearchPage"
import LivePage from './pages/LivePage';
import WebcamUploadPage from './pages/WebcamUploadPage.jsx';
import FileUploadPage from './pages/FileUploadPage.jsx';

function Routes() {
    const router = createBrowserRouter([
        {
            path: "/",
            element: <SearchPage />,
        },
        {
            path: "/live",
            element: <LivePage />,
        },
        {
            path: "/webcamupload",
            element: <WebcamUploadPage />,
        },
        {
            path: "/fileupload",
            element: <FileUploadPage />,
        }
    ]);

    return (
        <RouterProvider router={router} fallbackElement={<SearchPage />} />
    )
}

export default Routes
