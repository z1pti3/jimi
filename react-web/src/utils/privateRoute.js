import React from 'react';
import { Route, Redirect } from 'react-router-dom';
import { PollAuth } from './../components/login.component'

// handle the private routes
function PrivateRoute({ component: Component, ...rest }) {
  return (
    <Route
      {...rest}
      render={(props) => PollAuth() ? <Component {...props} /> : <Redirect to={{ pathname: '/login', state: { from: props.location } }} />}
    />
  )
}
 
export default PrivateRoute;