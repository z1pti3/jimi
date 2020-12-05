import React, { Component } from "react";
import { useHistory } from 'react-router-dom';

import configData from "./../config/config.json";

import { setUserSession, removeUserSession } from './../utils/common';

import "./html.component.css"
import "./login.component.css"

export function Logout(props) {   
    removeUserSession();
    const history = useHistory()
    setTimeout(() => { history.push('/login'); }, 2500);
    return (
        <div className="fullscreen">
            <h1>jimi</h1>
            <div className="outer">
                <div className="inner">
                    <h3>Successfully logged out</h3>
                </div>
            </div>
        </div>
    );
}

export class Login extends Component {
    constructor(props) {
        super(props);
        this.state = {
            username: null,
            password: null,
            otpRequired: false,
            otp: null,
            failedLogin: false
        }
        this.submit = this.submit.bind(this);
        this.change = this.change.bind(this);
    }

    submit(event) {
        event.preventDefault();
        this.setState({ failedLogin: false });

        if (!this.state.otpRequired) {
            const requestOptions = {
                method: 'POST',
                mode: configData.cosMode,
                body: JSON.stringify({ username: this.state.username, password: this.state.password })
            };
            fetch(configData.url+configData.uri+'auth/', requestOptions).then(response => {
                if (response.ok) return response;
                throw response;
            }).then(response => {
                setUserSession("1", "test");
                this.props.history.push('/'); 
            }).catch(error => { 
                this.setState({ otpRequired: true });
            });
        } else {
            const requestOptions = {
                method: 'POST',
                mode: configData.cosMode,
                body: JSON.stringify({ username: this.state.username, password: this.state.password, otp: this.state.otp })
            };
            fetch(configData.url+configData.uri+'auth/', requestOptions).then(response => {
                if (response.ok) return response;
                throw response;
            }).then(response => {
                this.props.history.push('/index'); 
            }).catch(error => { 
                this.setState({ otpRequired: false });
                this.setState({ failedLogin: true });
            });
        }
    }

    change(event) {
        const target = event.target;
        var value = target.value;
        const name = target.name;
        if (target.type === 'checkbox') {
            if (target.checked) {
                this.state.hobbies[value] = value;   
            } else {
                this.state.hobbies.splice(value, 1);
            }
        } else {
            this.setState({ [name]: value });
        }   
    }

    render() {
        return (
            <div className="fullscreen">
                <h1>jimi</h1>
                <div className="outer">
                    <div className={`inner ${!this.state.failedLogin ? "" : "shake"}`}>
                        <form onSubmit={this.submit}>
                            <h3>Login</h3>
                            {this.state.failedLogin ? <p className="failedLoginAlert"><b>Login details appear to be invalid!</b></p> : <p className="failedLoginAlert"><b>&#160;</b></p> }
                            <div className="form-group">
                                <input type="text" name="username" className="form-control textbox" placeholder="Username" autoComplete="off" onChange={this.change} />
                            </div>

                            <div className="form-group">
                                <input type="password" name="password" className="form-control textbox" placeholder="password" autoComplete="off" onChange={this.change} />
                            </div>

                            {this.state.otpRequired &&
                                <div className="form-group">
                                    <input type="text" name="otp" className="form-control textbox" placeholder="One Time Password" autoComplete="off" onChange={this.change} />
                                </div>
                            }

                            <button type="submit" className="btn btn-primary btn-block button">Login</button>
                        </form>
                    </div>
                </div>
            </div>
        );
    }
}