import React from "react";
import { BrowserRouter, Switch, Route, NavLink } from 'react-router-dom';

import PublicRoute from './../utils/publicRoute';
import Login from './login.component';

import './topbar.component.css'

function Topbar(props) {   
    return (
            <div class="container" id="topbar">
                <h4>
                    jimi
                </h4>
                <BrowserRouter>
                    <NavLink exact className="link" activeClassName="active" to="/conducts">Conducts</NavLink>
                    <NavLink exact className="link" activeClassName="active" to="/administrator">Administrator</NavLink>
                    <NavLink exact className="link" activeClassName="active" to="/login">Login</NavLink>
                    <Switch>
                        <PublicRoute path="/login" component={Login} />
                    </Switch>
                </BrowserRouter>
            </div>
    );
  }
  export default Topbar;