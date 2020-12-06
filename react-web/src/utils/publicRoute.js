import React from 'react';
import { Route, Redirect } from 'react-router-dom';
import { PollAuth } from './../components/login.component'

import { isActiveSession } from './../utils/session';
 
// handle the public routes
function PublicRoute({ component: Component, ...rest }) {
  return (
    <Route
      {...rest}
      render={(props) => <Component {...props} /> }
    />
  )
}
 
export default PublicRoute;