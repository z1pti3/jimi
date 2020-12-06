import React from 'react';
import { Route, Redirect } from 'react-router-dom';
import { PollAuth } from './../components/login.component'

import { isActiveSession } from './../utils/session';

// handle the private routes
function PrivateRoute({ component: Component, ...rest }) {
  PollAuth();
  return (
    <Route
      {...rest}
      render={(props) => isActiveSession() ? <Component {...props} /> : <Redirect to={{ pathname: '/login', state: { from: props.location } }} />}
    />
  )
}
 
export default PrivateRoute;