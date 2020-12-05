import React from "react";
import { BrowserRouter, Switch, Route, NavLink } from 'react-router-dom';

import { getUser } from './../utils/common';

import PublicRoute from './../utils/publicRoute';
import PrivateRoute from './../utils/privateRoute';
import {Login, Logout} from './login.component';
import Status from '../pages/status.page';

import './topbar.component.css'

function Topbar(props) {   
    return (
        <BrowserRouter>
            <div class="container" id="topbar">
                <NavLink exact className="home" activeClassName="homeActive" to="/">jimi</NavLink>
                <NavLink exact className="link" activeClassName="active" to="/status">Status</NavLink>
                <NavLink exact className="link" activeClassName="active" to="/conducts">Conducts</NavLink>
                <NavLink exact className="link" activeClassName="active" to="/plugins">Plugins</NavLink>
                <NavLink exact className="link" activeClassName="active" to="/codify">Codify</NavLink>
                <NavLink exact className="link" activeClassName="active" to="/modelEditor">Model Editor</NavLink>
                <div class="container" id="topbar-right">
                    { getUser ? <NavLink exact className="link linkRight" activeClassName="active" to="/logout">Logout</NavLink> : null }
                    { getUser ? <NavLink exact className="link linkRight" activeClassName="active" to="/myAccount">My Account</NavLink> : null }
                    { getUser ? <NavLink exact className="link linkRight" activeClassName="active" to="/administration">Administration</NavLink> : null }
                </div>
            </div>
            <Switch>
                <PublicRoute path="/login" component={Login} />
                <PrivateRoute path="/logout" component={Logout} />
                <PrivateRoute path="/status" component={Status} />
                <PrivateRoute path="/conducts" component={Status} />
                <PrivateRoute path="/plugins" component={Status} />
                <PrivateRoute path="/codify" component={Status} />
                <PrivateRoute path="/modelEditor" component={Status} />
                <PrivateRoute path="/administration" component={Status} />
                <PrivateRoute path="/" component={Status} />
            </Switch>
        </BrowserRouter>
    );
  }
  export default Topbar;