import React, { Component } from "react";

import configData from "./../config/config.json";

import ConductList from "./../components/conductList.component"

import "./conducts.page.css"

export default class Conducts extends Component {
    constructor(props) {
        super(props);
        this.state = {
            conducts: [],
            filter: ""
        }

        const requestOptions = {
            method: 'GET',
            credentials: 'include',
            mode: configData.cosMode
        };
        fetch(configData.url+configData.uri+'conducts/', requestOptions).then(response => {
            if (response.ok) {
                return response.json()
            }
        }).then(json => {
            this.setState({ conducts : json["results"] });
        });

        this.change = this.change.bind(this);
        this.DeleteConduct = this.DeleteConduct.bind(this);
        this.NewConduct = this.NewConduct.bind(this);
    }

    NewConduct() {
        this.props.history.push('/conductSettings/');
    }

    DeleteConduct(e,id,name) {
        if (window.confirm("Please confirm removal of conduct named "+name)) {
            const requestOptions = {
                method: 'DELETE',
                credentials: 'include',
                mode: configData.cosMode
            };
            fetch(configData.url+configData.uri + 'models/conduct/' + id + "/", requestOptions).then(response => {
                if (response.ok) {
                    this.setState({ conducts: this.state.conducts.filter(conduct => conduct._id !== id) });
                }
                throw response;
            }).catch(error => {
                console.log("Could not delete conduct: " + id)
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
            <div className="pageContent1">
                <div>
                    <input type="text" name="filter" className="form-control textbox conductSearch" placeholder="Search Conducts" onChange={this.change} />
                    <br/>
                    <button className="btn btn-primary btn-block button conductNew" onClick={this.NewConduct}>+ Create New</button>
                </div>
                <br/>
                <div>
                    <ConductList conducts={this.state.conducts} filter={this.state.filter} deleteConductClickHandler={this.DeleteConduct} />
                </div>
            </div>
        );
    }
}