import React, { Component } from "react";

import { getSessionCSRF } from './../utils/session';

import configData from "./../config/config.json";

import "./../components/html.component.css"
import "./conductSettings.page.css"

export default class ConductSettings extends Component {
    constructor(props) {
        super(props);
        this.state = {
            type: "New",
            name: "",
            status: false,
            comment: "",
            loading: true,
            updateStatus: { "id" : null, "msg" : "" } 
        }
        this.change = this.change.bind(this);
        this.submit = this.submit.bind(this);

        const search = props.location.search;
        const conductID = new URLSearchParams(search).get('conductID');
        const edit = new URLSearchParams(search).get('edit');
        if (edit === "True") {
            const requestOptions = {
                method: 'GET',
                credentials: 'include',
                mode: configData.cosMode
            };
            fetch(configData.url+configData.uri+'models/conduct/'+conductID+"/", requestOptions).then(response => {
                if (response.ok) {
                    return response.json()
                }
            }).then(json => {
                this.setState({ "name" : json["name"], "status" : json["status"], "comment" : json["comment"], "type" : "Update", "loading" : false })
            });
        } else {
            this.state["loading"] = false;
        }
    }

    submit(event) {
        event.preventDefault();
        const search = this.props.location.search;
        const conductID = new URLSearchParams(search).get('conductID');
        const edit = new URLSearchParams(search).get('edit');
        var data = { CSRF: getSessionCSRF(), name: this.state.name, comment: this.state.comment, enabled: this.state.enabled }
        if (edit === "True") {
            const requestOptions = {
                method: 'POST',
                credentials: 'include',
                mode: configData.cosMode,
                body: JSON.stringify(data)
            };
            fetch(configData.url+configData.uri+'models/conduct/'+conductID+"/", requestOptions).then(response => {
                if (response.ok) return response;
                throw response;
            }).then(response => {
                
            }).catch(error => { 
                
            });
        } else {
            const requestOptions = {
                method: 'PUT',
                credentials: 'include',
                mode: configData.cosMode
            };
            fetch(configData.url+configData.uri+'models/conduct/', requestOptions).then(response => {
                if (response.ok) return response.json();
                throw response;
            }).then(response => {
                // put returns an ID number that can then be used to push the data within the form to - this is a two step process
                requestOptions["method"] = "POST"
                requestOptions["body"] = JSON.stringify(data)
                fetch(configData.url+configData.uri+'models/conduct/'+response["_id"]+"/", requestOptions).then(response => {
                    if (response.ok) return response;
                    throw response;
                }).then(response => {
                    
                }).catch(error => { 
                    
                });
            }).catch(error => { 
                
            });
        }
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
                    <h3>Conduct Details</h3>
                    <br/><br/>
                    <div className="form-group">
                        General Details
                        <hr/>
                    </div>                    
                    <div className="form-group">
                        Name:
                        <input type="text" name="name" className="form-control textbox" autoComplete="off" value={this.state.name} onChange={this.change} />
                    </div>
                    <div className="form-group">
                        Comment:
                        <input type="text" name="comment" className="form-control textbox" autoComplete="off" value={this.state.comment} onChange={this.change} />
                    </div>
                    <br/>

                    <br/>
                    <button type="submit" className="btn btn-primary btn-block button small">{this.state.type}</button>
                </form>
            </div>
        ) : <span>Loading page...</span>
    }
}