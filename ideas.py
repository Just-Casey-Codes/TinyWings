@app.route('/send_mission/<int:dragon_id>', methods=['POST'])
@login_required
def send_mission(dragon_id):
    cost = 10  # Cost of sending a dragon
    user = current_user

    if user.points >= cost:
        user.points -= cost
        db.session.commit()
        flash("Your dragon is on a mission!", "success")
    else:
        flash("Not enough points to send a dragon.", "danger")

    return redirect(url_for('dashboard'))