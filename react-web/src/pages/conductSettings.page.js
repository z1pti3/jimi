import React, { Component } from "react";

import { getSessionCSRF } from './../utils/session';

import configData from "./../config/config.json";
import { URL } from"./../utils/api";


import "./../components/html.component.css"
import "./conductSettings.page.css"

export default class ConductSettingsPage extends Component {
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
            };
            fetch(URL()+'models/conduct/'+conductID+"/", requestOptions).then(response => {
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
                body: JSON.stringify(data)
            };
            fetch(URL()+'models/conduct/'+conductID+"/", requestOptions).then(response => {
                if (response.ok) return response;
                throw response;
            }).then(response => {
                
            }).catch(error => { 
                
            });
        } else {
            const requestOptions = {
                method: 'PUT',
                credentials: 'include',
                body: JSON.stringify({ CSRF: getSessionCSRF() })
            };
            fetch(URL()+'models/conduct/', requestOptions).then(response => {
                if (response.ok) return response.json();
                throw response;
            }).then(response => {
                // put returns an ID number that can then be used to push the data within the form to - this is a two step process
                requestOptions["method"] = "POST"
                requestOptions["body"] = JSON.stringify(data)
                var conductID = response["_id"]
                fetch(URL()+'models/conduct/'+conductID+"/", requestOptions).then(response => {
                    if (response.ok) return response;
                    throw response;
                }).then(response => {
                    this.props.history.push('?conductID='+conductID+'&edit=True');
                    // Force reload of this screen
                    window.location.reload(false);
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
                        <textarea type="text" name="comment" className="form-control textarea" autoComplete="off" value={this.state.comment} onChange={this.change} />
                    </div>
                    <br/>

                    <br/>
                    <button type="submit" className="btn btn-primary btn-block button small">{this.state.type}</button>
                </form>
            </div>
        ) : <span>Loading page...</span>
    }
}