import React from "react";
import { BrowserRouter, Switch, Route, NavLink } from 'react-router-dom';

import { isActiveSession } from './../utils/session';

import PublicRoute from './../utils/publicRoute';
import PrivateRoute from './../utils/privateRoute';
import {Login, Logout} from './login.component';

import Status from '../pages/status.page';
import MyAccount from '../pages/myAccount.page'; 
import Conducts from '../pages/conducts.page'; 
import Conduct from '../pages/conduct.page'; 
import ConductSettings from '../pages/conductSettings.page'; 
import Plugins from '../pages/plugins.page'; 
import Plugin from '../pages/plugin.page'; 
import ModelEditor from '../pages/modelEditor.page'; 
import Codify from '../pages/codify.page'; 



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
                    { isActiveSession ? <NavLink exact className="link linkRight" activeClassName="active" to="/logout">Logout</NavLink> : null }
                    { isActiveSession ? <NavLink exact className="link linkRight" activeClassName="active" to="/myAccount">My Account</NavLink> : null }
                    { isActiveSession ? <NavLink exact className="link linkRight" activeClassName="active" to="/administration">Administration</NavLink> : null }
                </div>
            </div>
            <Switch>
                <PublicRoute path="/login" component={Login} />
                <PrivateRoute path="/logout" component={Logout} />
                <PrivateRoute path="/status" component={Status} />
                <PrivateRoute path="/conducts" component={Conducts} />
                <PrivateRoute path="/conduct" component={Conduct} />
                <PrivateRoute path="/conductSettings" component={ConductSettings} />
                <PrivateRoute path="/plugins" component={Plugins} />
                <PrivateRoute path="/plugin" component={Plugin} />
                <PrivateRoute path="/codify" component={Codify} />
                <PrivateRoute path="/modelEditor" component={ModelEditor} />
                <PrivateRoute path="/myAccount" component={MyAccount} />
                <PrivateRoute path="/administration" component={Status} />
                <PrivateRoute path="/" component={Status} />
            </Switch>
        </BrowserRouter>
    );
  }
  export default Topbar;