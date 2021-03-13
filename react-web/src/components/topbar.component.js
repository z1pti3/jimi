import React from "react";
import { BrowserRouter, Switch, Route, NavLink } from 'react-router-dom';

import { isActiveSession } from './../utils/session';

import PublicRoute from './../utils/publicRoute';
import PrivateRoute from './../utils/privateRoute';
import {Login, Logout} from './login.component';

import StatusPage from '../pages/status.page';
import MyAccountPage from '../pages/myAccount.page'; 
import ConductsPage from '../pages/conducts.page'; 
import ConductPage from '../pages/conduct.page'; 
import ConductSettingsPage from '../pages/conductSettings.page'; 
import PluginsPage from '../pages/plugins.page'; 
import PluginPage from '../pages/plugin.page'; 
import ModelEditorPage from '../pages/modelEditor.page'; 
import CodifyPage from '../pages/codify.page'; 
import AdminPage from '../pages/admin.page'; 
import CleanupPage from '../pages/cleanup.page';
import MarketplacePage from '../pages/marketplace.page';
import FilesPage from '../pages/files.page';



import './topbar.component.css'

function Topbar(props) {   
    return (
        <BrowserRouter>
            <div class="container" id="topbar">
                <NavLink exact className="home" activeClassName="homeActive" to="/">jimi</NavLink>
                <NavLink exact className="link" activeClassName="active" to="/status">Status</NavLink>
                <NavLink exact className="link" activeClassName="active" to="/conducts">Conducts</NavLink>
                {/* <NavLink exact className="link" activeClassName="active" to="/files">Files</NavLink> */}
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
                <PrivateRoute path="/status" component={StatusPage} />
                <PrivateRoute path="/conducts" component={ConductsPage} />
                <PrivateRoute path="/conduct" component={ConductPage} />
                <PrivateRoute path="/files" component={FilesPage} />
                <PrivateRoute path="/conductSettings" component={ConductSettingsPage} />
                <PrivateRoute path="/plugins" component={PluginsPage} />
                <PrivateRoute path="/plugin" component={PluginPage} />
                <PrivateRoute path="/codify" component={CodifyPage} />
                <PrivateRoute path="/modelEditor" component={ModelEditorPage} />
                <PrivateRoute path="/myAccount" component={MyAccountPage} />
                <PrivateRoute path="/administration" component={AdminPage} />
                <PrivateRoute path="/marketplace" component={MarketplacePage} />
                <PrivateRoute path="/cleanup" component={CleanupPage} />
                <PrivateRoute path="/" component={StatusPage} />
            </Switch>
        </BrowserRouter>
    );
  }
  export default Topbar;