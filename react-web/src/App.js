import React from 'react';
import { BrowserRouter, Switch, Route, NavLink } from 'react-router-dom';

import './app.css';

import PrivateRoute from './utils/privateRoute';
import PublicRoute from './utils/publicRoute';
 
import Login from './components/login.component';
import Dashboard from './dashboard';
import Home from './home';
 
function App() {
  return (
    <BrowserRouter>
      <div className="App">
          <div>
            <div className="header">
              <NavLink exact activeClassName="active" to="/">Home</NavLink>
              <NavLink activeClassName="active" to="/login">Login</NavLink><small>(Access without token only)</small>
              <NavLink activeClassName="active" to="/dashboard">Dashboard</NavLink><small>(Access with token only)</small>
            </div>
            <Switch>
              <Route exact path="/" component={Home} />
              <PublicRoute path="/login" component={Login} />
              <PrivateRoute path="/dashboard" component={Dashboard} />
            </Switch>
          </div>
      </div>
    </BrowserRouter>
  );
}
 
export default App;