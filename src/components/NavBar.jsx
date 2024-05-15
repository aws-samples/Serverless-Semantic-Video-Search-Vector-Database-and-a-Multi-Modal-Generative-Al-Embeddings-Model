import PropTypes from 'prop-types'
import { signOut, signInWithRedirect } from 'aws-amplify/auth';
import TopNavigation from "@cloudscape-design/components/top-navigation";

const NavBar = (props) => {

    const loginlogout = async (isAuthenticated) => {
        if (isAuthenticated){
            await signOut()
        } else {
            await signInWithRedirect({
                provider: "AmazonFederate"
            });    
        }
    }

    return (
        <TopNavigation
            identity={{
                href: "/",
                title: props.title,
            }}
            utilities={[
                {
                    type: "button",
                    variant: "link",
                    text: props.isAuthenticated? "Sign out "+ props.user.username : "Sign in",
                    onFollow: () => loginlogout(props.isAuthenticated)
                }
            ]}
        >

        </TopNavigation>
    )
}

NavBar.propTypes = {
    title: PropTypes.string,
    isAuthenticated: PropTypes.bool
}

export default NavBar;
