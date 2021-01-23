import React, { Component } from "react";

import { getSessionCSRF } from './../utils/session';

import configData from "./../config/config.json";

import "./../components/html.component.css"
import "./myAccount.page.css"

export default class MyAccount extends Component {
    constructor(props) {
        super(props);
        this.state = {
            username: null,
            name: null,
            password: "",
            password1: "",
            password2: "",
            updated: false,
            updateFailed: false,
            msg: "",
            loading: true
        }
        this.change = this.change.bind(this);
        this.submit = this.submit.bind(this);

        const requestOptions = {
            method: 'GET',
            credentials: 'include',
            mode: configData.cosMode
        };
        fetch(configData.url+configData.uri+'auth/myAccount/', requestOptions).then(response => {
            if (response.ok) {
                return response.json()
            }
        }).then(json => {
            this.setState({ "username" : json["username"], "name" : json["name"], "loading" : false })
        });
    }

    submit(event) {
        event.preventDefault();
        if (this.state.password1 !== this.state.password2) {
            this.setState({ msg: "Passwords do not match" })
            this.setState({ updateFailed: true });
            setTimeout(() => { this.setState({ updateFailed: false }) }, 1000);
            return
        }
        var data = { CSRF: getSessionCSRF(), name: this.state.name }
        if (this.state.password1 !== "")
        {
            data["password"] = this.state.password
            data["password1"] = this.state.password1
        }
        const requestOptions = {
            method: 'POST',
            credentials: 'include',
            mode: configData.cosMode,
            body: JSON.stringify(data)
        };
        fetch(configData.url+configData.uri+'auth/myAccount/', requestOptions).then(response => {
            if (response.ok) return response;
            throw response;
        }).then(response => {
            this.setState({ msg: "Saved" })
            this.setState({ updated: true })
            setTimeout(() => { this.setState({ updated: false }) }, 1000);
        }).catch(error => { 
            this.setState({ msg: "Error: Could not save data" })
            this.setState({ updateFailed: true });
        });
    }

    change(event) {
        this.setState({ updateFailed: false, msg: "" });
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
        return !this.state.loading ? (
            <div className="pageContent2">
                <form onSubmit={this.submit}>
                    <h3>Your Details</h3>
                    <br/><br/>
                    <div className="form-group">
                        General Details
                        <hr/>
                    </div>                    
                    <div className="form-group">
                        Username:
                        <br/>
                        <input type="text" name="username" className="form-control textbox" autoComplete="off" value={this.state.username} disabled="true" onChange={this.change} />
                    </div>

                    <div className="form-group">
                        Name:
                        <br/>
                        <input type="text" name="name" className="form-control textbox" autoComplete="off" value={this.state.name} onChange={this.change} />
                    </div>
                    <br/>

                    <div className="form-group">
                        Change Password
                        <hr/>
                    </div>
                    <div className="form-group">
                        Current Password:
                        <br/>
                        <input type="password" name="password" className="form-control textbox" autoComplete="off" onChange={this.change} />
                    </div>
                    <div className="form-group">
                        New Password:
                        <br/>
                        <input type="password" name="password1" className={`form-control textbox ${this.state.msg == "Passwords do not match" ? "alertErrorBorder" : ""}`} autoComplete="off" onChange={this.change} />
                    </div>
                    <div className="form-group">
                        Confirm New Password:
                        <br/>
                        <input type="password" name="password2" className={`form-control textbox ${this.state.msg == "Passwords do not match" ? "alertErrorBorder" : ""}`} autoComplete="off" onChange={this.change} />
                    </div>

                    <br/>
                    <button type="submit" className={`btn btn-primary btn-block button small ${!this.state.updated ? "" : "saved"} ${!this.state.updateFailed ? "" : "error"}`}>Update</button>
                    <p className={`resultMessage ${!this.state.updateFailed ? "alert" : "alertError"} ${!this.state.updated && !this.state.updateFailed ? "hide" : ""}`}><b>{this.state.msg}</b></p>
                </form>
            </div>
        ) : <span>Loading page...</span>
    }
}