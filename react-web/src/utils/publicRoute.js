import React from 'react';
import { Route, Redirect } from 'react-router-dom';
import { PollAuth } from './../components/login.component'
 
// handle the public routes
function PublicRoute({ component: Component, ...rest }) {
  return (
    <Route
      {...rest}
      render={(props) => !PollAuth() ? <Component {...props} /> : <Redirect to={{ pathname: '/dashboard' }} />}
    />
  )
}
 
export default PublicRoute;